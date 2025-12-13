## AV device link lights but no connectivity (structured checklist)

1) Confirm basics: correct VLAN/port, cabling seated, link speed/duplex auto.
2) Ping local gateway/from host; check IP/subnet mask/gateway/DNS.
3) Check device DHCP vs static; ensure no IP conflict; ARP table sanity.
4) Test another known-good port/cable; swap to isolated switch if possible.
5) Verify controller?s service is running; check vendor admin page if available offline.
6) Disable/adjust local firewall briefly (if policy allows) to test.
7) Check LLDP/CDP info to confirm correct switch/path.
8) If still failing, packet capture on the port (mirrored) to see ARP/DHCP/traffic; note absence suggests mis-VLAN or ACL.
