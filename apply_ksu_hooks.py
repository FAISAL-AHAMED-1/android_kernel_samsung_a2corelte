#!/usr/bin/env python3
"""
Install KernelSU-Next manual hooks into a Linux 3.18 (Samsung a2corelte) tree.

Run from the kernel source root:
    python3 apply_ksu_hooks.py            # apply
    python3 apply_ksu_hooks.py --dry-run  # show what would change

Safe to run twice (already-patched files are skipped). If an anchor is not
found the script stops for that hook, prints FAILED, and exits non-zero
without touching that file, so nothing is left half-edited.
"""
import os
import re
import sys

DRY = "--dry-run" in sys.argv
ROOT = os.getcwd()
failed = []
changed = []


def path(p):
    return os.path.join(ROOT, p)


def read(p):
    with open(path(p), newline="") as f:
        return f.read()


def write(p, s):
    if DRY:
        return
    with open(path(p), "w", newline="") as f:
        f.write(s)


def find_line(lines, regex, start=0):
    rx = re.compile(regex)
    for i in range(start, len(lines)):
        if rx.search(lines[i]):
            return i
    return -1


def patch_file(p, marker, edits):
    """edits: list of (func_regex, anchor_regex, where, text, decl_text)
    - func_regex : line that starts the function (used to bound the search)
    - anchor_regex: first line after it that we insert relative to
    - where: 'before' or 'after' the anchor line
    - text: code inserted at the anchor
    - decl_text: extern declaration inserted just above the function line
    """
    if not os.path.exists(path(p)):
        failed.append("%s: file not found" % p)
        return
    src = read(p)
    if marker in src:
        print("skip   %-34s (already patched)" % p)
        return
    lines = src.split("\n")
    # apply edits bottom-to-top is unnecessary; recompute indexes each time
    for (func_rx, anchor_rx, where, text, decl) in edits:
        fi = find_line(lines, func_rx)
        if fi < 0:
            failed.append("%s: function not found (%s)" % (p, func_rx))
            return
        ai = find_line(lines, anchor_rx, fi)
        if ai < 0:
            failed.append("%s: anchor not found after '%s' (%s)" % (p, lines[fi].strip(), anchor_rx))
            return
        ins = ai if where == "before" else ai + 1
        lines[ins:ins] = text.rstrip("\n").split("\n")
        if decl:
            lines[fi:fi] = decl.rstrip("\n").split("\n") + [""]
    write(p, "\n".join(lines))
    changed.append(p)
    print("patched %-33s" % p)


def hook(text):
    return "#ifdef CONFIG_KSU_MANUAL_HOOK\n%s\n#endif" % text.rstrip("\n")


# --------------------------------------------------------------------------
# 1. fs/exec.c  -> do_execve_common (covers execve + compat execve)
patch_file("fs/exec.c", "ksu_handle_execveat", [(
    r"^static int do_execve_common\(",
    r"return PTR_ERR\(filename\);",
    "after",
    hook("\t{\n\t\tint ksu_fd = AT_FDCWD;\n\n"
         "\t\tksu_handle_execveat(&ksu_fd, &filename, &argv, &envp, NULL);\n\t}"),
    hook("extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr,\n"
         "\t\t\t\t     void *argv, void *envp, int *flags);"),
)])

# 2. fs/open.c -> faccessat
patch_file("fs/open.c", "ksu_handle_faccessat", [(
    r"^SYSCALL_DEFINE3\(faccessat,",
    r"if \(mode & ~S_IRWXO\)",
    "before",
    hook("\tksu_handle_faccessat(&dfd, &filename, &mode, NULL);"),
    hook("extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user,\n"
         "\t\t\t\t int *mode, int *__unused_flags);"),
)])

# 3. fs/stat.c -> vfs_fstatat (stat/lstat/newfstatat), plus fstat return hooks
patch_file("fs/stat.c", "ksu_handle_stat", [
    (r"^int vfs_fstatat\(",
     r"if \(\(flag & ~\(AT_SYMLINK_NOFOLLOW",
     "before",
     hook("\tksu_handle_stat(&dfd, &filename, &flag);"),
     hook("extern int ksu_handle_stat(int *dfd, const char __user **filename_user,\n"
          "\t\t\t   int *flags);")),
    (r"^SYSCALL_DEFINE2\(newfstat,",
     r"^\s*return error;",
     "before",
     hook("\tksu_handle_newfstat_ret(&fd, &statbuf);"),
     hook("extern void ksu_handle_newfstat_ret(unsigned int *fd,\n"
          "\t\t\t\t  struct stat __user **statbuf_ptr);")),
])
# fstat64 only exists when the arch wants stat64; patch it separately/optionally
if os.path.exists(path("fs/stat.c")) and "ksu_handle_fstat64_ret" not in read("fs/stat.c") \
        and "SYSCALL_DEFINE2(fstat64," in read("fs/stat.c"):
    patch_file("fs/stat.c", "ksu_handle_fstat64_ret", [
        (r"^SYSCALL_DEFINE2\(fstat64,",
         r"^\s*return error;",
         "before",
         hook("\tksu_handle_fstat64_ret(&fd, &statbuf);"),
         hook("extern void ksu_handle_fstat64_ret(unsigned long *fd,\n"
              "\t\t\t\t  struct stat64 __user **statbuf_ptr);")),
    ])

# 4. fs/read_write.c -> vfs_read (init.rc proxy)
patch_file("fs/read_write.c", "ksu_handle_vfs_read", [(
    r"^ssize_t vfs_read\(struct file \*file,",
    r"if \(!\(file->f_mode & FMODE_READ\)\)",
    "before",
    hook("\tksu_handle_vfs_read(&file, &buf, &count, &pos);"),
    hook("extern int ksu_handle_vfs_read(struct file **file_ptr, char __user **buf_ptr,\n"
         "\t\t\t     size_t *count_ptr, loff_t **pos);"),
)])

# 5. reboot syscall (manager <-> kernel channel). Kbuild requires the symbol
#    to appear in kernel/reboot.c, so refuse to patch anything else.
reboot_file = None
for cand in ("kernel/reboot.c", "kernel/sys.c"):
    if os.path.exists(path(cand)) and "SYSCALL_DEFINE4(reboot," in read(cand):
        reboot_file = cand
        break
if reboot_file is None:
    failed.append("reboot syscall (SYSCALL_DEFINE4(reboot,) not found in kernel/reboot.c or kernel/sys.c")
elif reboot_file != "kernel/reboot.c":
    failed.append("reboot syscall lives in %s, but KernelSU's Kbuild only looks in kernel/reboot.c; "
                  "tell Claude and the Kbuild check will be adjusted" % reboot_file)
else:
    patch_file(reboot_file, "ksu_handle_sys_reboot", [(
        r"^SYSCALL_DEFINE4\(reboot,",
        r"capable\(.*CAP_SYS_BOOT\)",
        "before",
        hook("\tksu_handle_sys_reboot(magic1, magic2, cmd, &arg);"),
        hook("extern int ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd,\n"
             "\t\t\t\t  void __user **arg);"),
    )])

# 6. drivers/input/input.c -> input_event (volume-down safe mode)
patch_file("drivers/input/input.c", "ksu_handle_input_handle_event", [(
    r"^void input_event\(struct input_dev \*dev,",
    r"if \(is_event_supported\(type, dev->evbit, EV_MAX\)\)",
    "before",
    hook("\tksu_handle_input_handle_event(&type, &code, &value);"),
    hook("extern int ksu_handle_input_handle_event(unsigned int *type, unsigned int *code,\n"
         "\t\t\t\t\t int *value);"),
)])

# 7. security/security.c -> what the LSM hooks do on 4.2+ kernels.
#    3.18 has no security_add_hooks(), so call the handlers directly.
patch_file("security/security.c", "ksu_handle_setresuid", [
    (r"^int security_task_fix_setuid\(",
     r"return security_ops->task_fix_setuid",
     "before",
     hook("\tksu_handle_setresuid(__kuid_val(old->uid), __kuid_val(new->uid));"),
     hook("extern int ksu_handle_setresuid(uid_t old_uid, uid_t new_uid);")),
    (r"^int security_inode_rename\(",
     r"^\{",
     "after",
     hook("\tksu_inode_rename(old_dir, old_dentry, new_dir, new_dentry);"),
     hook("extern int ksu_inode_rename(struct inode *old_dir, struct dentry *old_dentry,\n"
          "\t\t\t\t struct inode *new_dir, struct dentry *new_dentry);")),
    (r"^int security_key_permission\(",
     r"^\{",
     "after",
     hook("\tksu_key_permission(key_ref, cred, perm);"),
     hook("extern int ksu_key_permission(key_ref_t key_ref, const struct cred *cred,\n"
          "\t\t\t\t unsigned perm);")),
])

# 8. Header shim: 3.18 has no <linux/sched/signal.h>
shim = "include/linux/sched/signal.h"
if os.path.exists(path(shim)):
    print("skip   %-34s (exists)" % shim)
else:
    if not DRY:
        os.makedirs(os.path.dirname(path(shim)), exist_ok=True)
    write(shim, "/* compat shim for KernelSU on kernels older than 4.11 */\n"
                "#ifndef _LINUX_SCHED_SIGNAL_H_SHIM\n#define _LINUX_SCHED_SIGNAL_H_SHIM\n"
                "#include <linux/sched.h>\n#endif\n")
    changed.append(shim)
    print("created %-33s" % shim)

# 9. KernelSU-Next/kernel/hook/lsm_hooks.c -> make it build without
#    <linux/lsm_hooks.h> / security_add_hooks (kernels < 4.2)
lsm = "KernelSU-Next/kernel/hook/lsm_hooks.c"
if not os.path.exists(path(lsm)):
    failed.append(lsm + ": not found")
else:
    s = read(lsm)
    if "KSU_LEGACY_LSM" in s:
        print("skip   %-34s (already patched)" % lsm)
    else:
        ok = True
        # a) guard the header
        old = "#include <linux/lsm_hooks.h>\n"
        if old not in s:
            ok = False
            failed.append(lsm + ": include line not found")
        else:
            s = s.replace(old, "#include <linux/version.h>\n/* KSU_LEGACY_LSM: kernels < 4.2 have no LSM stacking */\n"
                          "#if LINUX_VERSION_CODE >= KERNEL_VERSION(4, 2, 0)\n#include <linux/lsm_hooks.h>\n#endif\n", 1)
        # b) make the handlers callable from security/security.c
        n1 = s.count("static int ksu_inode_rename(")
        s = s.replace("static int ksu_inode_rename(", "int ksu_inode_rename(")
        n2 = s.count("static int ksu_key_permission(")
        s = s.replace("static int ksu_key_permission(", "int ksu_key_permission(")
        if n1 == 0 or n2 == 0:
            ok = False
            failed.append(lsm + ": handler definitions not found (rename=%d key=%d)" % (n1, n2))
        # c) fence off the security_add_hooks() registration on old kernels
        a = s.find("static int ksu_task_fix_setuid(")
        b = s.rfind("#else\nvoid __init ksu_lsm_hook_init(void)")
        if a < 0 or b < 0 or b < a:
            ok = False
            failed.append(lsm + ": registration block markers not found")
        else:
            s = (s[:a] + "#if LINUX_VERSION_CODE >= KERNEL_VERSION(4, 2, 0)\n" + s[a:b] +
                 "#else /* < 4.2: handlers are called directly from security/security.c */\n"
                 "void __init ksu_lsm_hook_init(void)\n{\n\tpr_info(\"LSM hooks: legacy direct calls\\n\");\n}\n#endif\n" + s[b:])
        if ok:
            write(lsm, s)
            changed.append(lsm)
            print("patched %-33s" % lsm)

# 10. defconfig
dc = "arch/arm64/configs/exynos7870-a2corelte_defconfig"
if os.path.exists(path(dc)):
    s = read(dc)
    add = [l for l in ("CONFIG_KSU=y", "CONFIG_KSU_MANUAL_HOOK=y") if l not in s]
    if add:
        if not s.endswith("\n"):
            s += "\n"
        write(dc, s + "\n".join(add) + "\n")
        changed.append(dc)
        print("patched %-33s (+%s)" % (dc, ", ".join(add)))
    else:
        print("skip   %-34s (already has KSU options)" % dc)
else:
    failed.append(dc + ": not found")

print()
print("%s: %d file(s) %s" % ("DRY RUN" if DRY else "DONE", len(changed), "would change" if DRY else "changed"))
if failed:
    print("\nFAILED:")
    for f in failed:
        print("  -", f)
    sys.exit(1)
