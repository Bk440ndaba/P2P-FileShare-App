# Peer-to-Peer Torrent-Style File Sharing System

This is a simplified BitTorrent-style peer-to-peer file sharing system built using Python and socket programming. It enables users (leechers) to request and download files in parallel from multiple peers (seeders) and optionally become seeders themselves after successful download.

## Folder Structure

```
/NetworksAssignment
├── /SharedFiles/         # Directory for files to be seeded
├── UDPTracker.py         # Central Tracker managing metadata and seeders
├── Seeder.py             # Original Seeder program
├── SeederTwo.py          # Additional Seeder (for testing multiple seeders)
├── SeederThree.py        # Additional Seeder (for testing multiple seeders)
├── Leecher.py            # Command-line version of the Leecher
├── LeecherTwo.py         # GUI (Tkinter) version of the Leecher
└── README.md             # This file
```

## Features

- **Parallel Downloads** — File is split into chunks downloaded simultaneously from multiple seeders using threads
- **Round-Robin Chunk Assignment** — Ensures balanced chunk distribution across all available seeders
- **File Integrity Check** — Each chunk uses CRC32 checksum verification
- **Inactive Seeder Removal** — Tracker periodically removes unresponsive seeders
- **Re-Seeding** — Leechers can optionally transition into seeders post-download
- **Corrupt Chunk Recovery** — If a chunk is corrupted, the leecher automatically retries from other seeders
- **Last Chunk Handling** — Supports last chunk sizes smaller than the default chunk size
- **Tkinter GUI (Optional)** — User-friendly interface for downloading files

## How It Works

### Tracker (UDPTracker.py)

Acts as the central coordination point.

**Keeps track of:**
- Seeders and the chunks they have
- File metadata
- Receives heartbeat messages from seeders to ensure availability

**Responds to:**
- Seeder registration
- Leecher file requests

### Seeder (Seeder.py, SeederTwo.py, SeederThree.py)

- Reads a file from `/SharedFiles/`, splits it into chunks
- Registers with Tracker using UDP
- Listens for chunk requests via TCP and serves data with checksums

### Leecher (Leecher.py or LeecherTwo.py)

- Requests file from Tracker
- Downloads chunks in parallel using round-robin seeder allocation
- Verifies chunks using checksums
- After downloading, asks user whether to become a seeder

## Setup & Running

### Prerequisites

- Python 3.x
- Place all seedable files inside the `/SharedFiles/` directory

### 1. Run Tracker

```bash
python UDPTracker.py
```

### 2. Run Seeder(s)

```bash
python Seeder.py
python SeederTwo.py
python SeederThree.py
```

Ensure each Seeder uses a different port and reads a valid file from `/SharedFiles/`.

### 3. Run Leecher

**Command Line Leecher:**
```bash
python Leecher.py
```

**GUI Version (Optional):**
```bash
python LeecherTwo.py
```

## Notes

- For reseeding to work, `Seeder.py` must be available locally to the Leecher
- Default chunk size: 512KB
- Tracker must be started first

## Future Improvements

- Dynamic port allocation
- Torrent metadata files (like .torrent)
- Upload/download speed tracking
- File priority and pause/resume support
