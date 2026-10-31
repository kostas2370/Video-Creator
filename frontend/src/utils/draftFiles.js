let opening;

function database() {
  if (!opening) opening = new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") { reject(new Error("File recovery is unavailable")); return; }
    const request = indexedDB.open("viddie-creation-drafts", 1);
    request.onupgradeneeded = () => request.result.createObjectStore("files");
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error("File recovery is blocked"));
  }).catch(error => { opening = null; throw error; });
  return opening;
}

async function transaction(key, write, file) {
  const db = await database();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("files", write ? "readwrite" : "readonly");
    const store = tx.objectStore("files");
    const request = !write ? store.get(key) : file ? store.put({ blob: file, name: file.name, type: file.type, lastModified: file.lastModified }, key) : store.delete(key);
    let result;
    request.onsuccess = () => { result = request.result; };
    tx.oncomplete = () => resolve(result);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new Error("File recovery failed"));
  });
}

export async function readDraftFile(key) {
  const stored = await transaction(key, false);
  return stored?.blob ? new File([stored.blob], stored.name, { type: stored.type, lastModified: stored.lastModified }) : null;
}

export const writeDraftFile = (key, file) => transaction(key, true, file);
