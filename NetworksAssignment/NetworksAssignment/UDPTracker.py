import time
import threading
from socket import *

trackerPort = 15556


trackerSocket = socket(AF_INET, SOCK_DGRAM)
trackerSocket.bind(('localhost', trackerPort))  # We bind our socket to this trackerPort

print("Tracker is ready for requests.")

# Will keep a list of active seeders
seedersInfo = {}

#Method to remove inactive seeders, 
def removeInactiveSeeders():
    while True:
        currentTime = time.time()
        inactiveSeeders = []
        
        for seeder, data in list(seedersInfo.items()):
            #set timeout to 60 seconds, if not received add to inactive
            lastSeen = data.get("last seen", 0)
            timeSinceLastSeen = currentTime - lastSeen #Print this value
            
           # print(f"CTime of {seeder} is {currentTime} and Lseen {lastSeen} while timeseince is {timeSinceLastSeen}")
            
            if timeSinceLastSeen > 60:  
                  inactiveSeeders.append(seeder)
                  
        for seeder in inactiveSeeders:
            if seeder in seedersInfo:
                 print(f"Removed inactive seeder: {seeder}")
                 del seedersInfo[seeder]
                 
      #  print(seedersInfo) #just to check if delection really occured
           
        #check for inactive seeder after every 30 s 
        time.sleep(35)
        
#We'll use background threads to clean up inactive seeders
removerThread = threading.Thread(target=removeInactiveSeeders, daemon=True)
removerThread.start()
        

#Attempting to ensure we handling request concurrently by using Threads. Will start by creating method that we can can call

def requests(request, addr):
    global seedersInfo
    try:
        # We receive messages and check what type of request is it.
        message = request.decode().strip()  # want to also remove any extra white spaces

        print(f"Received request: '{message}' from {addr}")

        #Input from Seeder; Idea here is to use a map, all seeder file information mapped to seeder's IP and Port
        if message.startswith("register seeder"): 
            _, _, fileName, fileSize, chunkSize, numOfChunks = message.split()
            fileSize = int(fileSize)
            chunkSize = int(chunkSize)
            numOfChunks = int(numOfChunks)
            
            #We use seder address as the key
            seederKey = (addr[0], addr[1])
            
            #we check if seeder is already registered before storing it's info
            if seederKey in seedersInfo:
                trackerSocket.sendto("Seeder already registered.".encode(), addr)
                print(f"Seeder {addr} is already registered with file '{fileName}'.")
            else:
                seedersInfo[seederKey] = {
                    "filename": fileName,
                    "filesize": fileSize,
                    "chunksize": chunkSize,
                    "numOfchunks": numOfChunks,
                    "last seen": time.time()
                        
                }
                trackerSocket.sendto("Registration successful.".encode(), addr)
                print(f"Seeder at {addr} is registered with file '{fileName}' ({fileSize} bytes, {numOfChunks} chunks).") 

         ## print(seedersInfo) debbugging
         
         #we handle seeders activity update, each time it sends still active, we update that time
        elif message.startswith("active"):
             _, seederIP, seederPort = message.split()
             seederKey = (seederIP, int(seederPort))
             
             #We assume that our seederinfo will always contain a seederkey, different with inactive seeders[]
             if seederKey in seedersInfo:
                 seedersInfo[seederKey]["last seen"] = time.time()
                 print(f"active received from {seederKey}")
                     
                 
         #Handling Leecher's request
        elif message.startswith("requesting list of seeders with "):
            fileName = message.replace("requesting list of seeders with ", "")
            metadata = None # Will be sent to leecher
            
            #We gather every seeder that has the requested file
            seedersWithFile = [
                 (ip, port, details["filesize"], details["chunksize"], details["numOfchunks"])
                 for (ip, port), details in seedersInfo.items() if details["filename"] == fileName
            ]
            
            #Here we just use the details of the first seeder that has the file, since they'll alll have the same info
            if seedersWithFile:
                 fileSize, chunkSize, numOfChunks = seedersWithFile[0][2:5]
                 
                 #Constructing our metadata
                 metadata = f"file metadata {fileName} {fileSize} {chunkSize} {numOfChunks}\n"
                 metadata += "\n".join([f"{ip}:{port}" for ip, port, _, _, _ in seedersWithFile])
                 
            else:
                 metadata = "file not found"
                 
            trackerSocket.sendto(metadata.encode(), addr)
            print(f"Sent metadata for '{fileName}' to {addr}.")
            print(f"metadata : {metadata}")
                   

        else:
            # Handling reqyest we don't understand
            trackerSocket.sendto("Invalid request.".encode(), addr)
            print(f"Invalid request from {addr}: '{message}'")
    
    except Exception as e:
        print(f"An error occurred: {e}")
        
 # WE are going use this man loop call fundtion and start the threads
while True:
    try:
        request, addr = trackerSocket.recvfrom(2048)
        threading.Thread(target=requests, args=(request, addr)).start()
    except Exception as e:
        print(f"An error occurred in main loop: {e}")       

     
    
    
    
    
    
    
    
    
    
    
    
    



   
