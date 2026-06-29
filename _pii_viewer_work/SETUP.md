# Drive File Viewer — Setup Guide

## Step 1: Upload files to Google Drive

1. Open [Google Drive](https://drive.google.com)
2. Create a new folder (e.g. `PII-Persona-Files`)
3. Open the `extracted/` folder on your Mac and drag **both** `personas/` and `assets/` into the Drive folder
4. Wait for upload to complete (~160 MB)
5. Copy the **folder ID** from the URL:
   - URL looks like: `https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv`
   - The folder ID is: `1AbCdEfGhIjKlMnOpQrStUv`

## Step 2: Create the Apps Script project

1. Go to [script.google.com](https://script.google.com)
2. Click **New Project**
3. Rename it to `Drive File Viewer`

### Add `Code.gs`
4. The default file is already named `Code.gs` — replace its contents with the contents of the `Code.gs` file from this folder

### Add `Index.html`
5. Click the **+** next to "Files" → select **HTML**
6. Name it `Index` (it will become `Index.html`)
7. Paste the contents of the `Index.html` file from this folder

## Step 3: Deploy as Web App

1. Click **Deploy** → **New deployment**
2. Click the gear icon → select **Web app**
3. Set:
   - **Description**: Drive File Viewer
   - **Execute as**: Me
   - **Who has access**: Anyone (or Anyone within your org)
4. Click **Deploy**
5. **Authorize** when prompted (review permissions — it needs Drive access)
6. Copy the **Web app URL**

## Step 4: Use it

### Option A: Direct link with folder ID
Append `?folder=YOUR_FOLDER_ID` to the web app URL:
```
https://script.google.com/macros/s/DEPLOYMENT_ID/exec?folder=1AbCdEfGhIjKlMnOpQrStUv
```

### Option B: Landing page
Just open the web app URL without parameters — it shows a landing page where you can paste any folder link.

## Features

- **Universal**: Works with any Google Drive folder — just change the folder ID
- **Grid / List view**: Toggle between views
- **Inline preview**: Images, text files, JSON, CSV, Markdown, PDF, code
- **Search**: Recursive search across all subfolders (up to 200 results)
- **Download**: Direct download link for every file
- **Stats**: Shows total files, folders, and size in the header
- **Breadcrumb navigation**: Click any part to jump back
- **Mobile responsive**: Works on phones and tablets

## Sharing

To share with others:
1. Make sure the Drive folder is shared with them (View access is enough)
2. Share the web app URL with the `?folder=` parameter
3. They can browse, preview, and download everything
