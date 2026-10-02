#!/system/bin/sh
until [ -e /sys/class/misc/usb_mtp_gadget/dev ]; do sleep 1; done
M=$(cat /sys/class/misc/usb_mtp_gadget/dev)
rm -f /dev/mtp_usb
mknod /dev/mtp_usb c ${M%:*} ${M#*:}
chown system:mtp /dev/mtp_usb
chmod 0660 /dev/mtp_usb
chcon u:object_r:mtp_device:s0 /dev/mtp_usb
