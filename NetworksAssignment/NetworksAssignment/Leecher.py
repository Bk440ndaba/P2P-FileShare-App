from socket import *
import threading
import itertools
from tkinter import *
from tkinter.ttk import *
import time
import zlib
from Seeder import Startseeding

class Leecher:
    
    def __init__(self):
        self.trackerAddress = ('localhost', 15556)
        self.leecherUDPSocket = socket(AF_INET, SOCK_DGRAM)  # UDP socket for connecting to Tracker
        self.leecherPort = 10000
        self.leecherIP = '127.0.0.1'
    def download_file(self, filename, progress_callback=None):
        try:
            # Request message we are sending to tracker
            requestMessage = f"requesting list of seeders with {filename}"
            self.leecherUDPSocket.sendto(requestMessage.encode(), self.trackerAddress)
            
            if progress_callback:
                progress_callback(10, f"Sent file request to tracker for file: '{filename}'.")
            
            # Dealing with response from tracker after requesting file
            response, addr = self.leecherUDPSocket.recvfrom(4096)
            metadata = response.decode().strip()
            
            if metadata == "file not found":
                if progress_callback:
                    progress_callback(0, f"No seeder has the file '{filename}'.")
                return False
            
            else:
                # Handle metadata response from tracker
                metadataLines = metadata.split("\n")
                fileInfo = metadataLines[0].split()[2:]  # First line contains file details
                
                if progress_callback:
                    progress_callback(20, "File Found! Processing metadata...")
                
                # Extract file information
                filesize = int(fileInfo[1])
                chunksize = int(fileInfo[2])
                numberOfChunks = int(fileInfo[3])
                
                # Extract the seeders list
                seeders = metadataLines[1:]
                
                # Convert seeder address to format (IP, Port)
                seederAddresses = [tuple(seeder.split(":")) for seeder in seeders]
                
                # Assign chunks to seeders using Round-robin technique
                chunkAssignments = {}
                for chunk_index, seeder in zip(range(numberOfChunks), itertools.cycle(seederAddresses)):
                    chunkAssignments[chunk_index] = seeder  # Assign chunk to a Seeder
                
                # Storage for received chunks
                self.receivedChunks = {}
                
                # Start parallel download
                threads = []
                for chunk_index, (seeder_ip, seeder_port) in chunkAssignments.items():
                    thread = threading.Thread(
                        target=self._download_chunk, 
                        args=(chunk_index, seeder_ip, seeder_port, filename, chunksize, seeders, progress_callback)
                    )
                    thread.start()
                    threads.append(thread)
                
                # Wait for all threads to finish
                for thread in threads:
                    thread.join()
                
                if progress_callback:
                    progress_callback(90, "All chunks downloaded. Assembling file...")
                
                # Sort chunks and merge into a single file
                sortedChunks = [self.receivedChunks[i] for i in sorted(self.receivedChunks.keys())]
                with open(f"downloaded_{filename}", "wb") as f:
                    for chunk in sortedChunks:
                        f.write(chunk)  # Write chunk data in order
                
                if progress_callback:
                    progress_callback(100, f"Download complete! File saved as 'downloaded_{filename}'")
                
                return True
                
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"An error occurred: {e}")
            return False
            
        finally:   
            self.leecherUDPSocket.close()
    
    def _download_chunk(self, chunk_index, seeder_ip, seeder_port, filename, chunksize, seeders, progress_callback=None):
        validChunk = False
        
        try:
            # Create TCP socket for connecting to seeder
            leecherTCPSocket = socket(AF_INET, SOCK_STREAM)
            
            # Our leecher attempts to connect to seeder
            leecherTCPSocket.connect((seeder_ip, int(seeder_port)))
            
            if progress_callback:
                progress_callback(-1, f"Connected to Seeder {seeder_ip}:{seeder_port}")
            
            # After connection, leecher sends a chunk request from the seeder
            requestMessage = f"request_chunk {filename} {chunk_index}"  # Request is in the form of filename and index
            leecherTCPSocket.send(requestMessage.encode())
            
            # Function to receive all data
            def receive_all(sock, size):
                data = b""
                while len(data) < size:
                    packet = sock.recv(size - len(data))
                    if not packet:
                        return None
                    data += packet
                return data
            
            # Reading chunk size first (if protocol supports it)
            try:
                chunkBytes = receive_all(leecherTCPSocket, 4)
                if chunkBytes is None:
                    if progress_callback:
                        progress_callback(-1, f"Failed to read chunk size for chunk {chunk_index}")
                    return
                
                actualBytes = int.from_bytes(chunkBytes, "big")
                chunkData = receive_all(leecherTCPSocket, actualBytes)
                
            except:
                # Fallback if the protocol doesn't include size prefix
                chunkData = receive_all(leecherTCPSocket, chunksize)
            
            if chunkData is None:
                if progress_callback:
                    progress_callback(-1, f"Failed to receive chunk {chunk_index}")
                return
            
            try:
                # Try to receive checksum if protocol supports it
                receivedChecksum = int(leecherTCPSocket.recv(64).decode().strip())
                calculatedChecksum = zlib.crc32(chunkData)
                
                if calculatedChecksum == receivedChecksum:
                    self.receivedChunks[chunk_index] = chunkData
                    if progress_callback:
                        progress_callback(-1, f"Downloaded and verified chunk {chunk_index} from {seeder_ip}:{seeder_port}")
                    validChunk = True
                else:
                    if progress_callback:
                        progress_callback(-1, f"Chunk {chunk_index} failed checksum. Trying next seeder...")
                    
                    # Try other seeders if checksum fails
                    for nextSeeder in seeders:
                        nextSeederIP, nextSeederPort = nextSeeder.split(":")
                        if (nextSeederIP, nextSeederPort) == (seeder_ip, str(seeder_port)):
                            continue
                        
                        try:
                            altSocket = socket(AF_INET, SOCK_STREAM)
                            altSocket.connect((nextSeederIP, int(nextSeederPort)))
                            
                            if progress_callback:
                                progress_callback(-1, f"Trying alternative seeder for chunk {chunk_index}: {nextSeederIP}:{nextSeederPort}")
                            
                            altRequest = f"request_chunk {filename} {chunk_index}"
                            altSocket.send(altRequest.encode())
                            
                            # Try to read with size prefix first
                            try:
                                altChunkBytes = receive_all(altSocket, 4)
                                if altChunkBytes is None:
                                    continue
                                
                                altActualBytes = int.from_bytes(altChunkBytes, "big")
                                altChunkData = receive_all(altSocket, altActualBytes)
                            except:
                                # Fallback to fixed size
                                altChunkData = receive_all(altSocket, chunksize)
                            
                            if altChunkData is None:
                                continue
                            
                            try:
                                altChecksum = int(altSocket.recv(64).decode().strip())
                                altCalcChecksum = zlib.crc32(altChunkData)
                                
                                if altCalcChecksum == altChecksum:
                                    self.receivedChunks[chunk_index] = altChunkData
                                    if progress_callback:
                                        progress_callback(-1, f"Successfully downloaded chunk {chunk_index} from alternative seeder")
                                    validChunk = True
                                    break
                            except:
                                # If no checksum available, just accept the chunk
                                self.receivedChunks[chunk_index] = altChunkData
                                validChunk = True
                                break
                                
                            altSocket.close()
                        except Exception as e:
                            if progress_callback:
                                progress_callback(-1, f"Failed to connect to alternative seeder: {str(e)}")
            except:
                # If no checksum available in protocol, just accept the chunk
                self.receivedChunks[chunk_index] = chunkData
                if progress_callback:
                    progress_callback(-1, f"Downloaded chunk {chunk_index} from {seeder_ip}:{seeder_port}")
                validChunk = True
            
            leecherTCPSocket.close()
                
            if not validChunk:
                # If all seeders failed, just use the original chunk as a last resort
                if chunk_index not in self.receivedChunks and chunkData:
                    self.receivedChunks[chunk_index] = chunkData
                    if progress_callback:
                        progress_callback(-1, f"Using potentially corrupted chunk {chunk_index} as last resort")
                elif chunk_index not in self.receivedChunks:
                    if progress_callback:
                        progress_callback(-1, f"Failed to download chunk {chunk_index}")
                    
        except Exception as e:
            if progress_callback:
                progress_callback(-1, f"Error downloading chunk {chunk_index} from {seeder_ip}:{seeder_port}: {e}")
    
    def reseed(self, filename, leecherIP, leecherPort):
                Startseeding(
                    fileName= filename,
                    seederIP= self.leecherIP,
                    seederPort= 60000,
                    trackerAdress= self.trackerAddress
                )
                

class FileDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Downloader")
        
        fileFrame = Frame(root)
        fileFrame.pack(pady=10, fill="x", expand=True)  # Allow fileFrame to expand horizontally

        self.fileNameLabel = Label(fileFrame, text="File name:")
        self.fileNameLabel.pack(side=LEFT, padx=10)  # Keep label aligned left

        self.fileName = Entry(fileFrame)
        self.fileName.pack(side=LEFT, fill="x", expand=True, padx=10)      
        
        # Progress bar
        self.percent = StringVar()
        self.progBar = Progressbar(root, orient=HORIZONTAL, length=350)
        self.progBar.pack(pady=20)
        
        # Percent label
        self.percentLabel = Label(root, textvariable=self.percent)
        self.percentLabel.pack()
        
        # Status message
        self.statusVar = StringVar()
        self.statusVar.set("Ready")
        self.statusLabel = Label(root, textvariable=self.statusVar, wraplength=350)
        self.statusLabel.pack(pady=10)
        
        # Download button
        self.downloadButton = Button(root, text="Download File", command=self.startDownload)
        self.downloadButton.pack(pady=10)
        
        self.reseedButton = Button(root, text="Reseed To Seeder", command=self.reseeder)
        self.reseedButton.pack(pady=40)
        
        # Initialize leecher
        self.leecher = Leecher()
        
        # Track active downloads
        self.downloading = False
    def reseeder(self):
        if self.downloading:
            self.statusVar.set("Download is still in progress, Attempt reseed after download is complete")
            return
        file_name = self.fileName.get()
        
        reseed_thread = threading.Thread(target= self.leecher.reseed, args=(file_name,'127.0.0.1' ,60000))
        reseed_thread.daemon = True
        reseed_thread.start()
        
        self.statusVar.set("Successfully Transitioned Leecher as a Registered New Seeder")
    
    def startDownload(self):
        if self.downloading:
            self.statusVar.set("Download already in progress")
            return
            
        # Get the file name from the entry field
        file_name = self.fileName.get()
        if not file_name.strip():
            self.statusVar.set("Please enter a valid file name")
            return
        
        # Reset progress
        self.progBar['value'] = 0
        self.percent.set("0%")
        self.statusVar.set("Starting download...")
        self.downloading = True
        
        # Start download in a separate thread to keep GUI responsive
        download_thread = threading.Thread(target=self.performDownload, args=(file_name,))
        download_thread.daemon = True
        download_thread.start()
    
    def performDownload(self, file_name):
        try:
            # Call the leecher's download_file method with our update_progress callback
            success = self.leecher.download_file(file_name, self.update_progress)
            
            if not success:
                self.root.after(0, lambda: self.statusVar.set("Download failed. Please try again."))
        except Exception as e:
            self.root.after(0, lambda: self.statusVar.set(f"Error: {str(e)}"))
        finally:
            self.downloading = False
    
    def update_progress(self, progress, message):
        print(message, flush=True)
        # Special case: -1 means just update message, not progress
        if progress >= 0:
            time.sleep(0.5)

            # Update must be done in the main thread
            self.root.after(0, lambda: self.progBar.configure(value=progress))
            self.root.after(0, lambda: self.percent.set(f"{progress}%"))
        
        # Always update status message
        self.root.after(0, lambda: self.statusVar.set(message))


# Allow the file to be used as a module or standalone application
if __name__ == "__main__":
    # Create and run the GUI application
    window = Tk()
    app = FileDownloaderApp(window)
    window.mainloop()