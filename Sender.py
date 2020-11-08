from socket import *
import pickle
import sys
import time
import random
import hashlib
import threading


class Sender:
    def __init__(self, rec_h_ip, rec_port, file, MWS, MSS, gamma, pDrop, pDuplicate, pCorrupt, pOrder, maxOrder, pDelay,
                 maxDelay, seed):
        self.receiver_host_ip = rec_h_ip
        self.receiver_port = int(rec_port)
        self.file = file
        self.MWS = int(MWS)
        self.MSS = int(MSS)
        self.gamma = int(gamma)
        self.pDrop = float(pDrop)
        self.PDuplicate = float(pDuplicate)
        self.pCorrupt = float(pCorrupt)
        self.pOrder = float(pOrder)
        self.maxOrder = int(maxOrder)
        self.pDelay = float(pDelay)
        self.maxDelay = float(maxDelay)
        self.seed = int(seed)

    def Packet_Encapsulator(self, syn_num, ack_num, flags, checksum, returnACK):
        Packet = STP(syn_num, ack_num, "", flags, checksum, returnACK)
        return Packet

    def Packet_Data_Encapsulator(self, syn_num, ack_num, data, flags, checksum, returnACK):
        Packet = STP(syn_num, ack_num, data, flags, checksum, returnACK)
        return Packet

    socket = socket(AF_INET, SOCK_DGRAM)

    def STP_IP_Protocol_send(self, packet):
        self.socket.sendto(pickle.dumps(packet), (self.receiver_host_ip, self.receiver_port))
        return

    def STP_IP_Protocol_recieve(self):
        rdata, raddress = self.socket.recvfrom(2048)
        rpacket = pickle.loads(rdata)
        return rpacket

    def sender_log(self, event, time, pack_type, seq_no, pack_size, ack_no):
        f = open("Sender_log.txt", "a")
        if len(event) > 7:
            f.write("%s\t%.2f\t%s\t%d\t%d\t%d\n" % (event, round(time, 2), pack_type, seq_no, pack_size, ack_no))
        else:
            f.write("%s\t\t%.2f\t%s\t%d\t%d\t%d\n" % (event, round(time, 2), pack_type, seq_no, pack_size, ack_no))
        f.close()

    def fragmentFile(self, file, lPosition):
        if (lPosition + self.MSS < len(file)):
            fragmentedFile = file[lPosition:(lPosition + self.MSS)]
            newlPosition = lPosition + self.MSS

        elif (lPosition + self.MSS == len(file)):
            fragmentedFile = file[lPosition:(lPosition + self.MSS)]
            newlPosition = 0

        elif (lPosition + self.MSS > len(file)):
            fragmentedFile = file[lPosition:len(file)]
            newlPosition = 0
        return fragmentedFile, newlPosition

    def PLD_Runner_0(self, sequence_no, acknowledgement_no, file_to_transmit, last_position):
        global FASTTRANSLOCK
        #print("PLDRUNNER - 0", sequence_no)
        #print(sequence_no, acknowledgement_no, last_position)
        bundled_packet, last_position = Sender.fragmentFile(file_to_transmit, last_position)
        TransPack = Sender.Packet_Data_Encapsulator(sequence_no, acknowledgement_no, bundled_packet, 0,
                                                    hashlib.md5(bundled_packet).hexdigest(), 2)
        while (FASTTRANSLOCK == True):
            pass
        Sender.STP_IP_Protocol_send(TransPack)
        # print("PLD 0 Packet sent with sequeence",sequence_no)
        curr_time = time.clock()
        Sender.sender_log("snd", curr_time - start_time, "D", TransPack.sequence_no, len(TransPack.data),
                          TransPack.acknowledgement_no)
        # print("sequence sent" ,sequence_no)
        sequence_no += len(bundled_packet)
        return sequence_no, acknowledgement_no, last_position

    def PLD_Runner_1(self, sequence_no, acknowledgement_no, file_to_transmit, last_position):
        bundled_packet, last_position = Sender.fragmentFile(file_to_transmit, last_position)
        # print("Packet dropped")
        TransPack = Sender.Packet_Data_Encapsulator(sequence_no, acknowledgement_no, bundled_packet, 0,
                                                    hashlib.md5(bundled_packet).hexdigest(), 2)
        curr_time = time.clock()
        Sender.sender_log("drop", curr_time - start_time, "D", TransPack.sequence_no, len(TransPack.data),
                          TransPack.acknowledgement_no)
        sequence_no += len(bundled_packet)
        return sequence_no, acknowledgement_no, last_position

    def PLD_Runner_2(self, sequence_no, acknowledgement_no, file_to_transmit, last_position):
        bundled_packet, last_position = Sender.fragmentFile(file_to_transmit, last_position)
        TransPack = Sender.Packet_Data_Encapsulator(sequence_no, acknowledgement_no, bundled_packet, 0,
                                                    hashlib.md5(bundled_packet).hexdigest(), 2)
        Sender.STP_IP_Protocol_send(TransPack)
        # print("PLD 2 Packet sent with sequeence", sequence_no)
        curr_time = time.clock()
        Sender.sender_log("snd", curr_time - start_time, "D", TransPack.sequence_no, len(TransPack.data),
                          TransPack.acknowledgement_no)
        Sender.STP_IP_Protocol_send(TransPack)
        # print("PLD 2 Duplicate Packet sent")
        curr_time = time.clock()
        Sender.sender_log("snd/dup", curr_time - start_time, "D", TransPack.sequence_no, len(TransPack.data),
                          TransPack.acknowledgement_no)
        sequence_no += len(bundled_packet)
        return sequence_no, acknowledgement_no, last_position

    def PLD_Runner_3(self, sequence_no, acknowledgement_no, file_to_transmit, last_position):
        bundled_packet, last_position = Sender.fragmentFile(file_to_transmit, last_position)
        b = b'\x01'
        TransPack = Sender.Packet_Data_Encapsulator(sequence_no, acknowledgement_no, bundled_packet, 0,
                                                    hashlib.md5(bundled_packet + b).hexdigest(), 2)
        Sender.STP_IP_Protocol_send(TransPack)

        curr_time = time.clock()
        Sender.sender_log("snd/corr", curr_time - start_time, "D", TransPack.sequence_no, len(TransPack.data),
                          TransPack.acknowledgement_no)
        sequence_no += len(bundled_packet)
        return sequence_no, acknowledgement_no, last_position

    def sendPackets(self, noFPack, sequence_no, acknowledgement_no, last_position, file_to_transmit):
        global curPack
        global data_processed
        global curr_seq_no
        global Acknowledgement
        global timeOut
        global lastACKPack
        global lastsequence
        global timerposn
        global timerActive
        global lastPacketAcknowledge
        global maindic
        global EstimatedRTT
        global devRTT
        global timedOUT
        global start_time
        global noOfSegments
        global noOfSDropped
        global noOfSCorr
        global noOfSRder
        global noOfSDup
        global noOfSDel
        global noOfSRtxTm
        global noOfSRtxFt
        global nextposn
        global noOfDupR
        global FASTTRANSLOCK

        FASTTRANSLOCK = False
        nextposn = 0
        noOfSRtxFt = 0
        noOfSRtxTm = 0
        noOfSDel = 0
        noOfSDup = 0
        noOfSRder = 0
        noOfSCorr = 0
        noOfSDropped = 0
        timedOUT = False
        maindic = {}
        lastPacketAcknowledge = False
        timerActive = False
        lastACKPack = 1
        lastsequence = 1
        timerposn = 0
        Acknowledgement = False
        packet_dropped = 0
        case = 0
        f = open(file, "rb")
        file_to_transmit = f.read()
        f.close()
        reOrderState = False
        delayState = False
        EstimatedRTT = 0.5
        devRTT = 0.25
        timeOut = EstimatedRTT + (self.gamma * devRTT)
        countdown = -1
        countdowntimer = 60000
        delaystart_time = -1
        timeoutSeq = 1
        timeoutposn = 0

        while data_processed <= len(file_to_transmit):

            if (countdown == 0 and reOrderState == True):
                #print("inside reorder gate")
                pack_start_time = time.clock()
                maindic[reOrderSequence] = pack_start_time

                bundled_packet, lp = Sender.fragmentFile(file_to_transmit, reorderLastPosn)
                TransPack = Sender.Packet_Data_Encapsulator(reOrderSequence, reOrderAcknowledgement, bundled_packet,
                                                            0, hashlib.md5(bundled_packet).hexdigest(), 2)
                Sender.STP_IP_Protocol_send(TransPack)
                curr_time = time.clock()
                Sender.sender_log("snd/rord", curr_time - start_time, "D", TransPack.sequence_no,
                                  len(TransPack.data),
                                  TransPack.acknowledgement_no)
                countdown = -1
                reOrderState = False
                noOfSegments += 1
                noOfSRder += 1


            elif ((time.clock() - delaystart_time) >= countdowntimer and delayState == True):
                #print("inside delay gate")
                pack_start_time = time.clock()
                maindic[delaySequence] = pack_start_time

                bundled_packet, lp = Sender.fragmentFile(file_to_transmit, delayLastPosn)
                TransPack = Sender.Packet_Data_Encapsulator(delaySequence, delayAcknowledgement, bundled_packet,
                                                            0, hashlib.md5(bundled_packet).hexdigest(), 2)
                Sender.STP_IP_Protocol_send(TransPack)
                curr_time = time.clock()
                Sender.sender_log("snd/dely", curr_time - start_time, "D", TransPack.sequence_no,
                                  len(TransPack.data), TransPack.acknowledgement_no)
                countdowntimer = -1
                delayState = False
                noOfSegments += 1
                noOfSDel += 1

            if curPack < noFPack:
                # print("seq_no send: ", sequence_no)
                if sequence_no <= len(file_to_transmit):
                    #print("sequence no is ",sequence_no)
                    case += 1
                    #print("inside PLD gate")
                    pld = PLD(pDrop, pDuplicate, pCorrupt, pOrder, pDelay, seed)
                    key, nextposn = pld.PLD_runner(nextposn)
                    #print("key",key)
                    #print("nextposn",nextposn)

                    if key == 0:
                        pack_start_time = time.clock()
                        maindic[sequence_no] = pack_start_time
                        #print("from normal gate")
                        sequence_no, acknowledgement_no, last_position = Sender.PLD_Runner_0(sequence_no,
                                                                                             acknowledgement_no,
                                                                                             file_to_transmit,
                                                                                             last_position)
                        noOfSegments += 1

                    if key == 1:
                        packet_dropped += 1
                        pack_start_time = time.clock()
                        maindic[sequence_no] = pack_start_time
                        sequence_no, acknowledgement_no, last_position = Sender.PLD_Runner_1(sequence_no,
                                                                                             acknowledgement_no,
                                                                                             file_to_transmit,
                                                                                             last_position)
                        noOfSegments += 1
                        noOfSDropped += 1


                    if key == 2:
                        pack_start_time = time.clock()
                        maindic[sequence_no] = pack_start_time
                        sequence_no, acknowledgement_no, last_position = Sender.PLD_Runner_2(sequence_no,
                                                                                             acknowledgement_no,
                                                                                             file_to_transmit,
                                                                                             last_position)
                        noOfSegments += 2
                        noOfSDup += 1

                    if key == 3:
                        pack_start_time = time.clock()
                        maindic[sequence_no] = pack_start_time
                        sequence_no, acknowledgement_no, last_position = Sender.PLD_Runner_3(sequence_no,
                                                                                             acknowledgement_no,
                                                                                             file_to_transmit,
                                                                                             last_position)
                        noOfSegments += 1
                        noOfSCorr += 1

                    if key == 4:
                        #print("PLDRUNNER - 4")
                        pack_start_time = time.clock()
                        maindic[sequence_no] = pack_start_time

                        if (reOrderState == False):
                            #print("Packet will be reordered in ", self.maxOrder)
                            countdown = self.maxOrder
                            reOrderState = True
                            reOrderSequence = sequence_no
                            reOrderAcknowledgement = acknowledgement_no
                            reorderLastPosn = last_position
                            tempFile, last_position = Sender.fragmentFile(file_to_transmit, reorderLastPosn)
                            #print(" length of tempfile = ", len(tempFile))
                            sequence_no += len(tempFile)


                        else:
                            #print("from reord gate")
                            sequence_no, acknowledgement_no, last_position = Sender.PLD_Runner_0(sequence_no,
                                                                                                 acknowledgement_no,
                                                                                                 file_to_transmit,
                                                                                                 last_position)
                            noOfSegments+=1

                    if key == 5:
                        pack_start_time = time.clock()
                        maindic[sequence_no] = pack_start_time

                        if (delayState == False):
                            delaystart_time = pack_start_time
                            factor = random.uniform(0, 1)
                            countdowntimer = factor * (self.maxDelay / 1000)
                            #print("countdown is :", countdowntimer)
                            delayState = True
                            delaySequence = sequence_no
                            delayAcknowledgement = acknowledgement_no
                            delayLastPosn = last_position
                            tempFile, last_position = Sender.fragmentFile(file_to_transmit, delayLastPosn)
                            #print(" length of tempfile = ", len(tempFile))
                            sequence_no += len(tempFile)


                        else:
                            #print("from delay gate")
                            sequence_no, acknowledgement_no, last_position = Sender.PLD_Runner_0(sequence_no,
                                                                                                 acknowledgement_no,
                                                                                                 file_to_transmit,
                                                                                                 last_position)
                            noOfSegments += 1


                curPack += 1
                if (countdown > 0):
                    countdown -= 1

                # #print('last data acknowledgement at sender',sequence_no)

            ##print("curPack =",curPack)
            if (curPack > 0):
              # #print(timerActive,timeoutSeq in maindic,timeoutSeq)
                if (timerActive == True and data_processed <= len(file_to_transmit) and timeoutSeq in maindic and maindic[timeoutSeq]):
                    if (timeoutSeq in maindic and maindic[timeoutSeq]):
                        k = 0
                        while (k < 200):
                            k += 1
                        cur_pack = maindic[timeoutSeq]
                        # #print("timer is active", time.clock() - cur_pack, timerActive, lastPacketAcknowledge, lastsequence)
                        if (lastPacketAcknowledge == False):
                            if ((time.clock() - cur_pack) >= timeOut):
                                #print("timeout")
                                pack_start_time = time.clock()
                                maindic[timeoutSeq] = pack_start_time
                                bundled_packet, lp = Sender.fragmentFile(file_to_transmit, timeoutposn - 1)
                                TransPack = Sender.Packet_Data_Encapsulator(timeoutSeq, acknowledgement_no,
                                                                            bundled_packet, 0,
                                                                            hashlib.md5(
                                                                                bundled_packet).hexdigest(),
                                                                            2)
                                Sender.STP_IP_Protocol_send(TransPack)
                                curr_time = time.clock()
                                Sender.sender_log("snd/RXT", curr_time - start_time, "D", TransPack.sequence_no,
                                                  len(TransPack.data),
                                                  TransPack.acknowledgement_no)

                                #print(timerActive)
                                #print(lastPacketAcknowledge)
                                timerActive = False
                                lastPacketAcknowledge = False
                                noOfSegments += 1
                                noOfSRtxTm += 1
                    else:
                        pass

                    # else:


                elif (data_processed < len(file_to_transmit)):
                    timerActive = True
                    lastPacketAcknowledge = False
                    timeoutSeq = lastsequence
                    timeoutposn = timerposn
                else:
                    timerActive = False
                    lastPacketAcknowledge = False

            # #print("Timer still Running")
            # #print("last position",last_position)
            # #print("data processed",data_processed)
            if last_position == 0 and reOrderState == False and delayState == False and data_processed >= len(file_to_transmit):
                break
           # #print("still running")
           # #print("lp",last_position)
           # #print("rord",reOrderState)
           # #print("delst",delayState)
           # #print("dp",data_processed)

    def initiateFIN(self, sequence_no, acknowledgement_no):
        global noOfSegments
        # #print("Fin sent by sender")
        SNDFIN = Sender.Packet_Encapsulator(sequence_no, acknowledgement_no, 1, 0, 2)
        Sender.STP_IP_Protocol_send(SNDFIN)
        noOfSegments += 1
        curr_time = time.clock()
        Sender.sender_log("snd", curr_time - start_time, "F", SNDFIN.sequence_no, len(SNDFIN.data),
                          SNDFIN.acknowledgement_no)

        # #print("Fin waiting by reciever")
        FINACK = Sender.STP_IP_Protocol_recieve()
        if FINACK.flags == 10:
            curr_time = time.clock()
            Sender.sender_log("rcv", curr_time - start_time, "A", FINACK.sequence_no, len(FINACK.data),
                              FINACK.acknowledgement_no)

        FINFIN = Sender.STP_IP_Protocol_recieve()
        if FINFIN.flags == 1:
            curr_time = time.clock()
            Sender.sender_log("rcv", curr_time - start_time, "F", FINFIN.sequence_no, len(FINFIN.data),
                              FINFIN.acknowledgement_no)

        acknowledgement_no += 1
        FINAL = Sender.Packet_Encapsulator(sequence_no, acknowledgement_no, 1, 0, 2)
        Sender.STP_IP_Protocol_send(FINAL)
        noOfSegments += 1
        curr_time = time.clock()
        Sender.sender_log("snd", curr_time - start_time, "A", FINAL.sequence_no, len(FINAL.data),
                          FINAL.acknowledgement_no)
        self.Finalprint()
        #print("total execution time", time.time() - clockst)

    def Finalprint(self):
        f = open("Sender_log.txt", "a")
        f.write("=============================================================")
        f.write("\nSize of the file (in Bytes)\t\t\t\t%d\n" % (len(file_to_transmit)))
        f.write("Segments transmitted (including drop & RXT)\t\t%d\n" % (noOfSegments))
        f.write("Number of Segments handled by PLD\t\t\t%d\n" % (((noOfSegments) - 4)))
        f.write("Number of Segments dropped\t\t\t\t%d\n" % (noOfSDropped))
        f.write("Number of Segments Corrupted\t\t\t\t%d\n" % (noOfSCorr))
        f.write("Number of Segments Re-ordered\t\t\t\t%d\n" % (noOfSRder))
        f.write("Number of Segments Duplicated\t\t\t\t%d\n" % (noOfSDup))
        f.write("Number of Segments Delayed\t\t\t\t%d\n" % (noOfSDel))
        f.write("Number of Retransmissions due to TIMEOUT\t\t%d\n" % (noOfSRtxTm))
        f.write("Number of FAST RETRANSMISSION\t\t\t\t%d\n" % (noOfSRtxFt))
        f.write("Number of DUP ACKS received\t\t\t\t%d\n" % (noOfDupR))
        f.write("=============================================================\n")
        f.close()

    def receivePackets(self, file):
        global curr_seq_no
        global curPack
        global duplicateACK
        global noOFDupliACK
        global timeOut
        global lastACKPack
        global lastsequence
        global timerposn
        global timerActive
        global lastPacketAcknowledge
        global data_processed
        global maindic
        global EstimatedRTT
        global devRTT
        global noOfSegments
        global noOfSRtxFt
        global noOfDupR
        global FASTTRANSLOCK
        global clockst

        FASTTRANSLOCK = False
        noOfDupR = 0
        lastPacketAcknowledge = False
        timerActive = False
        lastACKPack = 1
        lastsequence = 1
        timerposn = 0
        Last_Flag = 1
        last_successful_packet = 1
        last_packet = 1

        f = open(file, "rb")
        file_to_transmit = f.read()
        f.close()


        while True:
            ACKPack = Sender.STP_IP_Protocol_recieve()

            if (ACKPack.returnACK == 0 and ACKPack.acknowledgement_no == last_packet and Last_Flag == 1):
                #print("Received at Receiver at gate 3=", ACKPack.acknowledgement_no)
                last_packet = ACKPack.acknowledgement_no
                noOfDupR+=1
                duplicateACK = 0
                duplicateACK += 1
                #noOFDupliACK += 1
                curr_time = time.clock()
                #print("Received Duplicate Acknowledgement 1st time")
                #print(lastPacketAcknowledge)
                #print(timerActive)

                Last_Flag = 0

                Sender.sender_log("rcv/DA", curr_time - start_time, "A", ACKPack.sequence_no, len(ACKPack.data),
                                  ACKPack.acknowledgement_no)

            elif (ACKPack.returnACK == 0 and ACKPack.acknowledgement_no == last_packet and Last_Flag == 0):
                last_packet = ACKPack.acknowledgement_no

                noOfDupR+=1
               # noOFDupliACK += 1
                duplicateACK += 1
                curr_time = time.clock()
                #print("Received Duplicate Acknowledgement multiple time")
                #print(lastPacketAcknowledge)
                #print(timerActive)
                Last_Flag = 0
                Sender.sender_log("rcv/DA", curr_time - start_time, "A", ACKPack.sequence_no, len(ACKPack.data),
                                  ACKPack.acknowledgement_no)

            elif (ACKPack.returnACK == 1):
                #print("timeout is ", timeOut)
                #print("changeIProg=", changeIProg)
                RTT = ((time.clock()) - maindic[last_successful_packet])
                EstimatedRTT = EstimatedRTT * 0.875 + 0.125 * RTT
                devRTT = 0.75 * devRTT + 0.25 * abs(RTT - EstimatedRTT)
                timeOut = EstimatedRTT + self.gamma * devRTT
                if timeOut < 2:
                    timeOut = 2
                if timeOut > 60:
                    timeOut = 60
                data_processed += (ACKPack.acknowledgement_no - last_packet)
                no_of_hops = (ACKPack.acknowledgement_no - last_packet) / self.MSS
                curPack -= no_of_hops
                #print("new timeout is ", timeOut)
                #print("next packet to be called is ", ACKPack.acknowledgement_no)
                curr_time = time.clock()
                Sender.sender_log("rcv", curr_time - start_time, "A", ACKPack.sequence_no, len(ACKPack.data),
                                  ACKPack.acknowledgement_no)
                Last_Flag = 1
                k = 0
                while (k < 200):
                    k += 1
                last_packet = ACKPack.acknowledgement_no
                if (ACKPack.acknowledgement_no > 1):
                    last_successful_packet = ACKPack.acknowledgement_no - self.MSS
                lastsequence = ACKPack.acknowledgement_no
                timerposn = ACKPack.acknowledgement_no
                timerActive = False
                lastPacketAcknowledge = False
                #print("changeIProg=", changeIProg)
                #print("lastsequence =", lastsequence)
                #print("lastsequence in maindic at receiver", lastsequence in maindic)

            if (duplicateACK == 3):
                #print("FAST RETRANSMISSION")
                #print("timeout is",timeout)

                noOfSegments += 1
                noOfSRtxFt += 1
                duplicateACK = 0
                posn, lp = Sender.fragmentFile(file_to_transmit, ACKPack.acknowledgement_no - 1)
                FASTTRANSLOCK = True
                TransPack = Sender.Packet_Data_Encapsulator(ACKPack.acknowledgement_no, acknowledgement_no, posn, 0,
                                                            hashlib.md5(posn).hexdigest(), 2)
                curr_time = time.clock()
                Sender.STP_IP_Protocol_send(TransPack)
                pack_start_time = time.clock()
                maindic[sequence_no] = pack_start_time
                Sender.sender_log("snd/RXT", curr_time - start_time, "D", TransPack.sequence_no, len(TransPack.data),
                                  TransPack.acknowledgement_no)
                #print("Past Retranmission Packet sent")
                FTACKPack = Sender.STP_IP_Protocol_recieve()
                FASTTRANSLOCK = False

                next_sequence = FTACKPack.acknowledgement_no
                previous_sequence = ACKPack.acknowledgement_no
                no_of_hops = (next_sequence - previous_sequence) / self.MSS
                curPack -= no_of_hops
                data_processed += (next_sequence - previous_sequence)
                last_packet = FTACKPack.acknowledgement_no
                if ACKPack.acknowledgement_no < len(file_to_transmit):
                    #print("last successful packet is ", last_successful_packet)
                    RTT = ((time.clock()) - maindic[last_successful_packet])
                    EstimatedRTT = EstimatedRTT * 0.875 + 0.125 * RTT
                    devRTT = 0.75 * devRTT + 0.25 * abs(RTT - EstimatedRTT)
                    timeOut = EstimatedRTT + self.gamma * devRTT
                    if timeOut < 2:
                        timeOut = 2
                    if timeOut > 60:
                        timeOut = 60
                 #   print("new timeout is", timeout)
                    curr_time = time.clock()
                    Sender.sender_log("rcv", curr_time - start_time, "A", FTACKPack.sequence_no, len(FTACKPack.data),
                                      FTACKPack.acknowledgement_no)

                    lastPacketAcknowledge = False
                    timerActive = False


                    lastsequence = FTACKPack.acknowledgement_no
                    timerposn = FTACKPack.acknowledgement_no

                    #print("changeIProg=", changeIProg)
                    #print("lastsequence =", lastsequence)
                    ##print("lastsequence in maindic", lastsequence in maindic)
                    ##print("timer is ", maindic[lastsequence])
                else:
                    lastPacketAcknowledge = False
                    timerActive = False


            if ACKPack.acknowledgement_no > len(file_to_transmit):
                #print("data processed", data_processed)
                #print("initiating FIN from receiver")
                self.initiateFIN(sequence_no, acknowledgement_no)
                break


class STP:
    def __init__(self, s_num, a_num, data, Flags, checksum, returnACK):
        self.sequence_no = s_num
        self.acknowledgement_no = a_num
        self.data = data
        self.flags = Flags
        self.checksum = checksum
        self.returnACK = returnACK


class PLD:
    def __init__(self, pDrop, pDup, pCorrupt, pOrder, pDelay, seed):
        self.pDrop = float(pDrop)
        self.pDuplicate = float(pDup)
        self.pCorrupt = float(pCorrupt)
        self.pOrder = float(pOrder)
        self.pDelay = float(pDelay)
        self.seed = int(seed)

    def PLD_runner(self, nextposn):
        nextposn, value = self.next_number(nextposn, self.seed)
        if self.pDrop > value:
            return 1, nextposn
        nextposn, value = self.next_number(nextposn, self.seed)
        if self.pDuplicate > value:
            return 2, nextposn
        nextposn, value = self.next_number(nextposn, self.seed)
        if self.pCorrupt > value:
            return 3, nextposn
        nextposn, value = self.next_number(nextposn, self.seed)
        if self.pOrder > value:
            return 4, nextposn
        nextposn, value = self.next_number(nextposn, self.seed)
        if self.pDelay > value:
            return 5, nextposn
        return 0, nextposn

    def next_number(self, nextposn, seed):
        random.seed(seed)
        i = 0
        while (i <= nextposn):
            i += 1
            random.random()
        nextposn = i
        nextvalue = random.random()
        return nextposn, nextvalue


# initially SYN acknowledgement is set True

event = "Establish-SYN"
global sequence_no
global acknowledgement_no
global curr_seq_no
global curPack
global duplicateACK
global noOFDupliACK
global data_processed
global noOfSegments
global clockst

clockst = time.time()
noOfSegments = 0
data_processed = 0
curr_seq_no = 0
sequence_no = 0
acknowledgement_no = 0
curPack = 0
duplicateACK = 0
noOFDupliACK = 0
receiver_host_ip, receiver_port, file, MWS, MSS, gamma, pDrop, pDuplicate, pCorrupt, pOrder, maxOrder, pDelay, maxDelay, seed = sys.argv[
                                                                                                                                1:]
Sender = Sender(receiver_host_ip, receiver_port, file, MWS, MSS, gamma, pDrop, pDuplicate, pCorrupt, pOrder, maxOrder,
                pDelay, maxDelay, seed)
start_time = time.clock()
# Creating log files
f = open("Sender_log.txt", "w+")
f.close()
# Readying File
f = open(file, "rb")
file_to_transmit = f.read()
f.close()
last_position = 0
packet_dropped = 0
case = 0
noOPacks = int(int(MWS) / int(MSS))

if (event == "Establish-SYN"):
    #print("Sending SYN to Receiver")
    synEstb = Sender.Packet_Encapsulator(sequence_no, acknowledgement_no, 100, 0, 2)
    Sender.STP_IP_Protocol_send(synEstb)
    curr_time = time.clock()
    Sender.sender_log("snd", curr_time - start_time, "S", synEstb.sequence_no, len(synEstb.data),
                      synEstb.acknowledgement_no)
    noOfSegments += 1
    #print("ESTABLISHING CONNECTION")
    #print("SENT SYN")
    event = "Ackn-SYNACK"

if (event == "Ackn-SYNACK"):
    #print("Waiting for SYNACK....")
    synACKp = Sender.STP_IP_Protocol_recieve()
    if (synACKp.flags == 110):
        curr_time = time.clock()
        Sender.sender_log("rcv", curr_time - start_time, "SA", synACKp.sequence_no, len(synACKp.data),
                          synACKp.acknowledgement_no)
        #print("Recieved SYNACK....")
        acknowledgement_no = synACKp.sequence_no + 1
        sequence_no += 1
        noOfSegments += 1
        synACK = Sender.Packet_Encapsulator(sequence_no, acknowledgement_no, 10, 0, 2)
        Sender.STP_IP_Protocol_send(synACK)
        curr_time = time.clock()
        Sender.sender_log("snd", curr_time - start_time, "A", synACK.sequence_no, len(synACK.data),
                          synACK.acknowledgement_no)
        event = "Ready to Send"

if (event == "Ready to Send"):
    start_send = threading.Thread(target=Sender.sendPackets,
                                  args=(noOPacks, sequence_no, acknowledgement_no, last_position, file))
    start_send.start()

    start_receive = threading.Thread(target=Sender.receivePackets, args=(file,))
    start_receive.start()
sys.exit()
