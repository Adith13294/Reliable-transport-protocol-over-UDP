# Reliable transport protocol over UDP
 Reliable transport protocol over UDP

#creating a simple transport protocol (STP) using UDP with features borrowed from TCP

The STP protocol transfers pdf files from the sender to the receiver. And has 2 files sender and reciever. 

The sender file is initiated as:
python sender.py receiver_host_ip receiver_port file.pdf MWS MSS gamma pDrop pDuplicate pCorrupt pOrder maxOrder pDelay maxDelay seed