from socket import *
import pickle
import sys
import time
import hashlib


class STP:
    def __init__(self, seq_no, ack_no, data, Flags,checksum, returnACK):
        self.sequence_no = seq_no
        self.acknowledgement_no = ack_no
        self.data = data
        self.flags = Flags
        self.checksum = checksum
        self.returnACK = returnACK


class Receiver:
    def __init__(self, Rec_port, file):
        self.receiver_port = int(Rec_port)
        self.file = file

    def Packet_Encapsulator(self, syn_num, ack_num, flags,checksum,returnACK):
        Packet = STP(syn_num, ack_num, "", flags,checksum,returnACK)
        return Packet

    socket = socket(AF_INET, SOCK_DGRAM)

    def STP_IP_R_Protocol_send(self, packet, sender_address):
        self.socket.sendto(pickle.dumps(packet), (sender_address))
        return

    def STP_IP_R_Protocol_recieve(self):
        rdata, raddress = self.socket.recvfrom(2048)
        rpacket = pickle.loads(rdata)
        return rpacket, raddress

    def receiver_log(self, event, time , pack_type, seq_no, pack_size, ack_no):
        f =open("Receiver_log.txt","a")
        f.write ("%s\t%.2f\t%s\t%d\t%d\t%d\n" % (event, round(time,2) , pack_type, seq_no, pack_size, ack_no))
        f.close()

global sequence
global segRecv
global packs
global noOfScorr
global noOfDup
global noOfDupS

# Initial declarations
event = "Await-SYN"
sequence_no = 0
acknowledgement_no = 0
receiver_port = sys.argv[1]
file = sys.argv[2]
Receiver = Receiver(receiver_port, file)
Receiver.socket.bind(('', Receiver.receiver_port))
start_time = time.clock() 
f = open("Receiver_log.txt", "w+")

lastposn = 0
#Readying File to print
packs = []
sequence = []
segRecv = 0
noOfScorr = 0
noOfDup = 0
noOfDupS = 0
while True:
    if event == "Await-SYN":
        #print("Awaiting SYN from the sender")
        awaitSYN, Sender_address = Receiver.STP_IP_R_Protocol_recieve()
        segRecv += 1
        acknowledgement_no += 1
        if awaitSYN.flags == 100:
            curr_time = time.clock() 
            Receiver.receiver_log("rcv", curr_time - start_time, "S", awaitSYN.sequence_no, len(awaitSYN.data),
                              awaitSYN.acknowledgement_no)
            synACK= Receiver.Packet_Encapsulator(sequence_no, acknowledgement_no, 110, "",1)
            Receiver.STP_IP_R_Protocol_send(synACK, Sender_address)
            curr_time = time.clock() 
            Receiver.receiver_log("snd", curr_time - start_time, "SA", synACK.sequence_no, len(synACK.data),
                                  synACK.acknowledgement_no)

            sequence_no += 1
            event = "Await ACK"
        continue

    if (event == "Await ACK"):
        #print("Waiting for ACK....")
        awaitACK, Sender_address = Receiver.STP_IP_R_Protocol_recieve()
        segRecv += 1
        if (awaitACK.flags == 10):
            curr_time = time.clock() 
            Receiver.receiver_log("rcv", curr_time - start_time, "A", awaitACK.sequence_no, len(awaitACK.data),
                                  awaitACK.acknowledgement_no)

           # print("Acknowledgement Received....")
            event = "Ready to Recieve"
            f = open(file, "wb+")
            f.close()

        continue

    if (event == "Ready to Recieve"):
        while True:
            #print("Waiting for new File")
            if sequence_no in sequence:
                while(sequence_no in sequence):
                    ACKPack = packs[0]
                    acknowledgement_no += len(ACKPack.data)
                    f = open(file, "ab")
                    f.write(ACKPack.data)
                    f.close()
                    sequence_no += len(ACKPack.data)
                    lastposn += len(ACKPack.data)
                    del packs[0]

                SNDACK = Receiver.Packet_Encapsulator(1, acknowledgement_no, 0, "",1)
                Receiver.STP_IP_R_Protocol_send(SNDACK, Sender_address)
                curr_time = time.clock()
                Receiver.receiver_log("snd", curr_time - start_time, "A", SNDACK.sequence_no, len(SNDACK.data),
                                      SNDACK.acknowledgement_no)
                continue

            ACKPack, Sender_address = Receiver.STP_IP_R_Protocol_recieve()
            segRecv+=1
           # print("current sequence number is ",sequence_no)
           # print("current sequence no received is",ACKPack.sequence_no)
           # print("receiver sequence is ",sequence_no)

            if ACKPack.flags == 1:
                curr_time = time.clock() 
                Receiver.receiver_log("rcv", curr_time - start_time, "F", ACKPack.sequence_no, len(ACKPack.data),
                                      ACKPack.acknowledgement_no)
            #    print("Initiate FIN")
                event = "Initiate FIN"
                break

            elif ACKPack.sequence_no == sequence_no:
                if ACKPack.checksum == hashlib.md5(ACKPack.data).hexdigest():
                    acknowledgement_no += len(ACKPack.data)
             #       print("Packet Recieved",sequence_no)
                    f = open(file, "ab")
                    f.write(ACKPack.data)
                    f.close()
                    curr_time = time.clock()
                    Receiver.receiver_log("rcv", curr_time - start_time, "D", ACKPack.sequence_no, len(ACKPack.data),
                                          ACKPack.acknowledgement_no)
                    sequence_no += len(ACKPack.data)
                    lastposn += len(ACKPack.data)
                    if sequence_no not in sequence:
                        SNDACK = Receiver.Packet_Encapsulator(1, acknowledgement_no, 0, "",1)
                        Receiver.STP_IP_R_Protocol_send(SNDACK, Sender_address)
              #          print("Acknowledgement Sent")
                        curr_time = time.clock() 
                        Receiver.receiver_log("snd", curr_time - start_time, "A", SNDACK.sequence_no, len(SNDACK.data),
                                              SNDACK.acknowledgement_no)
                else:
               #     print("errored")
                    noOfScorr+=1

            elif ACKPack.sequence_no > sequence_no:
                if ACKPack.sequence_no not in sequence:
                    sequence.append(ACKPack.sequence_no)
                    packs.append(ACKPack)
                #    print("Future Packet received")
                    noOfDupS+=1
                    curr_time = time.clock()
                    Receiver.receiver_log("rcv", curr_time - start_time, "D", ACKPack.sequence_no, len(ACKPack.data),
                                          ACKPack.acknowledgement_no)
                    SNDACK = Receiver.Packet_Encapsulator(1, acknowledgement_no, 0, "",0)
                    Receiver.STP_IP_R_Protocol_send(SNDACK, Sender_address)
                 #   print("Duplicate Acknowledgement Sent",acknowledgement_no)
                    curr_time = time.clock()
                    Receiver.receiver_log("snd/DA", curr_time - start_time, "A", SNDACK.sequence_no, len(SNDACK.data),
                                          SNDACK.acknowledgement_no)
                else:
                    noOfDup += 1
                    noOfDupS += 1
                  #  print("Duplicate Packet Recieved")
                    curr_time = time.clock()
                    Receiver.receiver_log("rcv", curr_time - start_time, "D", ACKPack.sequence_no, len(ACKPack.data),
                                          ACKPack.acknowledgement_no)
                    SNDACK = Receiver.Packet_Encapsulator(1, acknowledgement_no, 0, "", 0)
                    Receiver.STP_IP_R_Protocol_send(SNDACK, Sender_address)
                   # print("Duplicate Acknowledgement Sent")
                    curr_time = time.clock()
                    Receiver.receiver_log("snd/DA", curr_time - start_time, "A", SNDACK.sequence_no, len(SNDACK.data),
                                          SNDACK.acknowledgement_no)



            elif ACKPack.sequence_no < sequence_no:
                noOfDup += 1
                noOfDupS += 1
               # print("Duplicate Packet Recieved")
                curr_time = time.clock() 
                Receiver.receiver_log("rcv", curr_time - start_time, "D", ACKPack.sequence_no, len(ACKPack.data),
                                      ACKPack.acknowledgement_no)
                SNDACK = Receiver.Packet_Encapsulator(1, acknowledgement_no, 0, "",0)
                Receiver.STP_IP_R_Protocol_send(SNDACK, Sender_address)
                #print("Duplicate Acknowledgement Sent")
                curr_time = time.clock() 
                Receiver.receiver_log("snd/DA", curr_time - start_time, "A", SNDACK.sequence_no, len(SNDACK.data),
                                      SNDACK.acknowledgement_no)

    if event == "Initiate FIN":
        #print("fin initiated")

        acknowledgement_no+=1
        FINACK = Receiver.Packet_Encapsulator(1, acknowledgement_no, 10, "",1)
        Receiver.STP_IP_R_Protocol_send(FINACK, Sender_address)
        curr_time = time.clock() 
        Receiver.receiver_log("snd", curr_time - start_time, "A", FINACK.sequence_no, len(FINACK.data),
                              FINACK.acknowledgement_no)
        FINFIN = Receiver.Packet_Encapsulator(1, acknowledgement_no, 1, "",1)
        Receiver.STP_IP_R_Protocol_send(FINFIN, Sender_address)
        curr_time = time.clock() 
        Receiver.receiver_log("snd", curr_time - start_time, "F", FINFIN.sequence_no, len(FINFIN.data),
                              FINFIN.acknowledgement_no)

        #print("fin initiated")
        SYSFIN, Sender_address = Receiver.STP_IP_R_Protocol_recieve()
        segRecv+=1
        if SYSFIN.flags == 1:
            curr_time = time.clock() 
            Receiver.receiver_log("rcv", curr_time - start_time, "A", SYSFIN.sequence_no, len(SYSFIN.data),
                                  SYSFIN.acknowledgement_no)
            event = "Print data"

    if event == "Print data":
        f = open("Receiver_log.txt", "a")
        f.write("=============================================================")
        f.write("\nAmount of data received (bytes)\t\t\t\t%d\n" % ((sequence_no - 1)))
        f.write("Total Segments Received\t\t\t\t\t%d\n" % (segRecv))
        f.write("Data segments received\t\t\t\t\t%d\n" % (((segRecv) - 4)))
        f.write("Data segments with Bit Errors\t\t\t\t%d\n" % (noOfScorr))
        f.write("Duplicate data segments received\t\t\t%d\n" % (noOfDup))
        f.write("Duplicate ACKs sent\t\t\t\t\t%d\n" % (noOfDupS))
        f.write("=============================================================\n")
        f.close()

    sys.exit()
