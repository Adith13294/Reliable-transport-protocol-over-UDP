# Reliable transport protocol over UDP
 Reliable transport protocol over UDP

# creating a simple transport protocol (STP) using UDP with features borrowed from TCP
 The STP protocol transfers pdf files from the sender to the receiver. And has 2 files sender and reciever. 

# The sender file is initiated as:
python sender.py receiver_host_ip receiver_port file.pdf MWS MSS gamma pDrop pDuplicate pCorrupt pOrder maxOrder pDelay maxDelay seed

# The receiver file is initiated as:
python receiver.py receiver_port file_r.pdf


# The overall architecture
![Capture qqPNG](https://user-images.githubusercontent.com/26299390/98464000-e9f80280-2213-11eb-978f-a48f784b1cda.PNG)
