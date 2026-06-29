/**
 * Universal Google Drive File Viewer — Apps Script Backend
 *
 * Deploy as a web app. Pass ?folder=<DRIVE_FOLDER_ID> to browse any folder.
 * If no folder param, it shows a landing page asking for a folder ID / link.
 */

function doGet(e) {
  var template = HtmlService.createTemplateFromFile("Index");
  template.rootFolderId = (e && e.parameter && e.parameter.folder) || "";
  return template
    .evaluate()
    .setTitle("Drive File Viewer")
    .addMetaTag("viewport", "width=device-width, initial-scale=1")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

/** List children of a folder. Returns { folders: [...], files: [...] } */
function listFolder(folderId) {
  var folder = DriveApp.getFolderById(folderId);
  var result = { name: folder.getName(), folders: [], files: [] };

  var subFolders = folder.getFolders();
  while (subFolders.hasNext()) {
    var f = subFolders.next();
    result.folders.push({ id: f.getId(), name: f.getName() });
  }
  result.folders.sort(function (a, b) {
    return a.name.localeCompare(b.name);
  });

  var files = folder.getFiles();
  while (files.hasNext()) {
    var file = files.next();
    result.files.push({
      id: file.getId(),
      name: file.getName(),
      mime: file.getMimeType(),
      size: file.getSize(),
      url: file.getUrl(),
      downloadUrl: file.getDownloadUrl(),
      updated: file.getLastUpdated().toISOString(),
    });
  }
  result.files.sort(function (a, b) {
    return a.name.localeCompare(b.name);
  });

  return result;
}

/** Get raw text content for text-based files (< 1 MB) */
function getTextContent(fileId) {
  var file = DriveApp.getFileById(fileId);
  if (file.getSize() > 1048576) return "(File too large for inline preview)";
  return file.getBlob().getDataAsString();
}

/** Get base64 image data for inline preview */
function getImageBase64(fileId) {
  var file = DriveApp.getFileById(fileId);
  if (file.getSize() > 5242880) return null;
  var blob = file.getBlob();
  var b64 = Utilities.base64Encode(blob.getBytes());
  return "data:" + blob.getContentType() + ";base64," + b64;
}

/** Search recursively in a folder tree */
function searchFiles(folderId, query) {
  var results = [];
  var q = query.toLowerCase();
  _searchRecursive(DriveApp.getFolderById(folderId), "", q, results, 200);
  return results;
}

function _searchRecursive(folder, path, query, results, limit) {
  if (results.length >= limit) return;
  var currentPath = path ? path + "/" + folder.getName() : folder.getName();

  var files = folder.getFiles();
  while (files.hasNext() && results.length < limit) {
    var file = files.next();
    if (file.getName().toLowerCase().indexOf(query) !== -1) {
      results.push({
        id: file.getId(),
        name: file.getName(),
        mime: file.getMimeType(),
        size: file.getSize(),
        path: currentPath,
        url: file.getUrl(),
        downloadUrl: file.getDownloadUrl(),
      });
    }
  }

  var subFolders = folder.getFolders();
  while (subFolders.hasNext() && results.length < limit) {
    _searchRecursive(subFolders.next(), currentPath, query, results, limit);
  }
}

/** Get folder stats (recursive count) */
function getFolderStats(folderId) {
  var stats = { files: 0, folders: 0, totalSize: 0 };
  _countRecursive(DriveApp.getFolderById(folderId), stats);
  return stats;
}

function _countRecursive(folder, stats) {
  var files = folder.getFiles();
  while (files.hasNext()) {
    var f = files.next();
    stats.files++;
    stats.totalSize += f.getSize();
  }
  var subs = folder.getFolders();
  while (subs.hasNext()) {
    stats.folders++;
    _countRecursive(subs.next(), stats);
  }
}
