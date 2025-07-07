import zlib
import threading
import time

from socket import*

trackerAdress = ('localhost', 15556)

seederIP = '127.0.0.1'
seederPort = 5001

fileName = "com-ug-handbook-6a-2025.pdf"
chunkSize = 512000
chunks = []
chunkCheckSums = []


## Here we need to get file size and calculate total num of Chucks before we can register with our tracker
try:
     with open(fileName, "rb") as f:
        fileData = f.read()  # Read full file as bytes
        fileSize = len(fileData) 
        
        # Split into chunks a
        for i in range(0, fileSize, chunkSize):
            chunk = fileData[i:i + chunkSize] 
            chunks.append(fileData[i:i + chunkSize])  # We use slicing to extract our btes and store them
            
            checkSum = zlib.crc32(chunk)
            chunkCheckSums.append(checkSum)
          
                
except FileNotFoundError:
    print(f"Error: File '{fileName}' not found!")
    exit()
    
numOfChunks = len(chunks)
#print(chunks)


## we then create a UDP socket to register with Tracker
seederUDPSocket = socket(AF_INET, SOCK_DGRAM)
seederUDPSocket.bind((seederIP, seederPort))

try:
    #Sending registartion request to Tracker
   registration = f"register seeder {fileName} {fileSize} {chunkSize} {numOfChunks}"
   seederUDPSocket.sendto(registration.encode(), trackerAdress)
   print(registration)
   
   #Dealing with registration response from tracker
   response, addr = seederUDPSocket.recvfrom(2048)
   print(response)
   
except Exception as e:
    print(f"An error occurred: {e}")
    

#Method to periodically update tracker about our activity
def sendActivity():
    while True:
        try:
            activityMsg = f"active {seederIP} {seederPort}"
            seederUDPSocket.sendto(activityMsg.encode(), trackerAdress)
            print("Sent active to Tracker")
        except Exception as e:
            print(f"Failed to send active: {e}")
        
        time.sleep(30)  # Wait 30 seconds 

activityThread = threading.Thread(target=sendActivity, daemon=True)
activityThread.start()

#seederUDPSocket.close() have to be moved, to allow continous sending of active status


#Start TCP Server to Handle Chunk Requests, bind socket to this port # and listen to on coming connections.
seederTCPSocket = socket(AF_INET, SOCK_STREAM)
seederTCPSocket.bind((seederIP, seederPort))  
seederTCPSocket.listen(5)  

print(f"Seeder is ready to send chunks at {seederIP}:{seederPort}")

while True:
    try:
        #Accept Connection from Leecher
        connectionSocket, addr = seederTCPSocket.accept()
        print(f"Connection established with Leecher {addr}")

        # Receive chunk request from Leecher
        request = connectionSocket.recv(1024).decode().strip()
        print(f"Received request: {request}")

        if request.startswith("request_chunk"):
            _, requestedFile, chunkIndex = request.split()
            chunkIndex = int(chunkIndex)

            # Send Requested Chunk
            if 0 <= chunkIndex < numOfChunks:
                chunkData = chunks[chunkIndex]  
                myCheckSum = chunkCheckSums[chunkIndex]
                
                
                if chunkIndex == numOfChunks - 1:
                     actualChunkSize = len(chunkData)
                     connectionSocket.sendall(actualChunkSize.to_bytes(4, "big")) 
                    
                else:
                    connectionSocket.sendall((chunkSize).to_bytes(4, "big"))
                
                
                connectionSocket.sendall(chunkData)  
                connectionSocket.sendall(str(myCheckSum).encode().ljust(64))
                #connectionSocket.send(str(myCheckSum).encode())
                
                print(f"Sent Chunk {chunkIndex} with checksum {myCheckSum} to {addr}")
            else:
                print(f"Invalid chunk request: {chunkIndex}")
                connectionSocket.send(b"Invalid chunk index")

        # Close connection after sending data
        connectionSocket.close()

    except Exception as e:
        print(f"Error while handling Leecher request: {e}")
        
   
