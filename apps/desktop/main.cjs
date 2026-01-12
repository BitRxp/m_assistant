const path = require('path');
const { app, BrowserWindow, dialog, shell } = require('electron');

function getIndexHtmlPath() {
  // apps/desktop/main.cjs -> apps/web/dist/index.html
  return path.resolve(__dirname, '..', 'web', 'dist', 'index.html');
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 780,
    backgroundColor: '#0b1020',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    }
  });

  // Allow microphone access from the renderer (getUserMedia)
  const ses = win.webContents.session;
  ses.setPermissionRequestHandler((webContents, permission, callback, details) => {
    if (permission === 'media' || permission === 'audioCapture' || permission === 'videoCapture') {
      callback(true);
      return;
    }
    callback(false);
  });

  const devUrl = process.env.DESKTOP_DEV_URL;
  if (devUrl) {
    win.loadURL(devUrl);
    win.webContents.openDevTools({ mode: 'detach' });
    return;
  }

  const indexHtml = getIndexHtmlPath();
  win.loadFile(indexHtml).catch(async (e) => {
    await dialog.showMessageBox(win, {
      type: 'error',
      title: 'm_assistant desktop',
      message: 'Web UI build not found',
      detail:
        'Expected: ' +
        indexHtml +
        '\n\nRun: cd apps/web && npm install && npm run build\nThen: cd apps/desktop && npm install && npm start\n\nError: ' +
        String(e)
    });
  });

  // Avoid navigation to arbitrary websites from within the app.
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
