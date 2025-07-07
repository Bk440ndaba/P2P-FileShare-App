import zlib

import threading
import itertools

from socket import *
from Seeder import Startseeding


trackerAddress = ('localhost', 15556) 

#seederAddress = ('137.158.62.200',5000)  ##new

leecherPort = 10000
leecherIP = '127.0.0.1'


leecherUDPSocket = socket(AF_INET, SOCK_DGRAM) ## UDP socket for connecting to Tracker
leecherUDPSocket.bind((leecherIP, leecherPort))

leecherTCPSocket = socket(AF_INET, SOCK_STREAM) ## TCP socket to connect to seeder, new
leecherTCPSocket.bind((leecherIP, leecherPort))

#validChunk = False


try:
    ##Request messge we are sending to tracker
    filename= input("Please enter name of the file you want to download: ").strip()
    requestMessage = f"requesting list of seeders with {filename}"
    leecherUDPSocket.sendto(requestMessage.encode(), trackerAddress)
    print(f"Sent file request to tracker for file : '{filename}'.")
    
    ##Dealing with response from tacker afer requesting file
    response, addr = leecherUDPSocket.recvfrom(4096)
    metadata = response.decode().strip()
    
    if metadata == "file not found":
        print(f"No seeder has the file '{filename}'.")
        exit()
    
    else:
        #Handle metadata response from tracker
        metadataLines = metadata.split("\n")
        fileInfo = metadataLines[0].split()[2:]   #First line contains file details
        
        print("\n File Found! Metadata:")
        print(f" filename: {fileInfo[0]}")
        
        filesize = int(fileInfo[1])
        print(f" filesize: {fileInfo[1]} bytes")
        
        chunksize = int(fileInfo[2])
        print(f" chunksize: {fileInfo[2]} bytes")
        
        numberOfChunks = int(fileInfo[3])
        print(f" numberOfChunks: {fileInfo[3]}")
        
        #lastly we extract the seeders list, slice from 1 because everything after that is just seeders
        seeders = []
        seeders = metadataLines[1:]
        print(f"List of seeders with the file '{filename}' : '{seeders}'")
        
        #Gonna try ann covert seeder address to this format(IP, Port)
        seederAddresses = [tuple(seeder.split(":")) for seeder in seeders]
        
        #We are assigning chunchk to seeders using Round-robin technique
        chunkAssignments = {}
        for chunk_index, seeder in zip(range(numberOfChunks), itertools.cycle(seederAddresses)):
            chunkAssignments[chunk_index] = seeder  # Assign chunk to a Seeder
            
        #Have a method to download chucnks using a tcp connect
        receivedChunks = {}
        
        #validChunk = False
        
        def download_chunk(chunk_index, seeder_ip, seeder_port):
            validChunk = False
            try:
               
                leecherTCPSocket = socket(AF_INET, SOCK_STREAM)

                #Our leechera attempts to connect to seeder
                leecherTCPSocket.connect((seeder_ip, int(seeder_port)))
                print(f"Connected to Seeder {seeder_ip}:{seeder_port}")

                # After connection, leecher sends a chunk request from the seeder
                requestMessage = f"request_chunk {filename} {chunk_index}" # Request is in the form of filename and index
                leecherTCPSocket.send(requestMessage.encode())

                # Recieving the requested chunk data and checksum
              #  chunkData = leecherTCPSocket.recv(chunksize)
               # receivedCheckSums = int(leecherTCPSocket.recv(64).decode())  #Incoming checksum 
                
                
                #Defining method to receive all chunks
                def receiveAll(sock, size):
                    data = b""
                    while len(data) < size:
                        packet = sock.recv(size - len(data))
                        if not packet:
                            return None
                        data += packet
                        
                    return data
                
                chunkBytes = receiveAll(leecherTCPSocket, 4)
                if chunkBytes is None:
                    print(f"Failed to read chunk size for chunk {chunk_index}")
                    return
                
                actualBytes = int.from_bytes(chunkBytes, "big") 
                
                chunkData = receiveAll(leecherTCPSocket, actualBytes)
                
                
                if chunkData is None:
                    print(f"Failed to receive chunk {chunk_index}")
                    return
                
                receivedCheckSums = int(leecherTCPSocket.recv(64).decode().strip())  #Incoming checksum 
                
        ##change made
                calculatedChecksum = zlib.crc32(chunkData) # calucated checksum
                
                print(f"Calculated checksum is {calculatedChecksum} and recevied is {receivedCheckSums}")
                
                #now just compatre the two checksums for error detections, if no match, request again from another seeder else move to next chunk
                if calculatedChecksum == receivedCheckSums:
                    receivedChunks[chunk_index] = chunkData
                    print(f"Downloaded and Verified Chunk {chunk_index} from {seeder_ip}:{seeder_port}")
                    return
                
                  
                 #here we re-download the same chunk index but from a different seeder, next possible seeder   
                else:
                     print(f"Chunk {chunk_index} from {seeder_ip} failed checksum. Trying next Seeder...")
                     
                    # validChunk = False
                     for nextSeederIP, nextSeederPort in seeders:
                         if(nextSeederIP, nextSeederPort) == (seeder_ip, seeder_port):
                             continue
                         
                         try:
                             leecherTCPSocket2 = socket(AF_INET, SOCK_STREAM)
                             leecherTCPSocket2.connect((nextSeederIP, int(nextSeederPort)))
                             
                             print(f"Attempting to re-download chunk {chunk_index} from Seeder at {seeder_ip} {seeder_port} ")
                             
                             
                             # sednong the same request for the chunk
                             requestMessage2 = f"request_chunk {filename} {chunk_index}"
                             leecherTCPSocket2.send(requestMessage2.encode())
                             
                             #dealing with response of chunk data + checksum
                             chunkData2 = receiveAll(leecherTCPSocket2, chunksize)
                             
                             ##Made change
                             receivedCheckSums2 = int(leecherTCPSocket2.recv(64).decode())
                             
                             calculatedChecksum2 = zlib.crc32(chunkData2)
                             #validChunk = False
                             
                             if calculatedChecksum2 == receivedCheckSums2:
                                 receivedChunks[chunk_index] = chunkData2
                                 print(f"Succefully found valid chunk {chunk_index} from another seeder at {nextSeederIP} {nextSeederPort}")
                                 validChunk = True
                                 break
                             
                             else:
                                 print(f"Chunk {chunk_index} failed a checksum, trying another seeder")
                                 
                             leecherTCPSocket2.close()
                              
                         except Exception as e:
                             
                             print("Can't Connect to seeder")
                             
                if not validChunk:
                    print(f"Chunk {chunk_index} not found. Download failed.")

                #Lastly close TCP connection after receiving chunk
                leecherTCPSocket.close()
            except Exception as e:
                print(f"Error downloading Chunk {chunk_index} from {seeder_ip}:{seeder_port}: {e}")
            
                
        #here we start with Parrallel download, we use threads
        threads = []
        for chunk_index, (seeder_ip, seeder_port) in chunkAssignments.items():
            thread = threading.Thread(target=download_chunk, args=(chunk_index, seeder_ip, seeder_port))
            thread.start()
            threads.append(thread)

        #wait for other threads to finish
        for thread in threads:
            thread.join()
            
        print("\n All the Chunks Downloaded. Assembling File...")
            
        
        # Sort Chunks and Merge into a Single File
        sortedChunks = [receivedChunks[i] for i in sorted(receivedChunks.keys())]
        with open(f"downloaded_{filename}", "wb") as f:
            for chunk in sortedChunks:
              f.write(chunk)  # Write chunk data in order

        print(f"Download Complete! File saved as 'downloaded_{filename}'") 
        
        
        ##Re-seeding process begings
        option = input("Want to become a seeder? (yes/no). ").strip().lower()
        if option == "yes":
            Startseeding(
                fileName= filename,
                seederIP= leecherIP,
                seederPort= 60000,
                trackerAdress= trackerAddress
            )
    
        
except Exception as e:
    print(f"An error occurred: {e}")
    
finally:   
    leecherUDPSocket.close()



                    







