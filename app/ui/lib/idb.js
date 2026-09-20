/** Minimal IndexedDB wrapper. The frontend owns conversation organisation;
 *  the backend keeps owning the model's rolling context window. */

const DB = 'kalki';
const VERSION = 1;
let dbp = null;

function open() {
  if (dbp) return dbp;
  dbp = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains('threads')) {
        const s = db.createObjectStore('threads', { keyPath: 'id' });
        s.createIndex('updatedAt', 'updatedAt');
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return dbp;
}

async function tx(store, mode, fn) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const t = db.transaction(store, mode);
    const req = fn(t.objectStore(store));
    t.oncomplete = () => resolve(req ? req.result : undefined);
    t.onerror = () => reject(t.error);
    t.onabort = () => reject(t.error);
  });
}

export const idb = {
  available: typeof indexedDB !== 'undefined',
  get: (id) => tx('threads', 'readonly', (s) => s.get(id)),
  put: (v) => tx('threads', 'readwrite', (s) => s.put(v)),
  del: (id) => tx('threads', 'readwrite', (s) => s.delete(id)),
  all: () => tx('threads', 'readonly', (s) => s.getAll()),
  clear: () => tx('threads', 'readwrite', (s) => s.clear()),
};
