const form = document.getElementById("setup-form");
const statusEl = document.getElementById("status");
const alreadyConnectedEl = document.getElementById("already-connected");
const connectionIdEl = document.getElementById("connection-id");

async function showExistingConnection() {
  const existing = await getStoredConnection();
  if (existing) {
    alreadyConnectedEl.hidden = false;
    connectionIdEl.textContent = existing.connectionId;
    form.hidden = true;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusEl.textContent = "Connecting...";
  statusEl.className = "";

  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  try {
    const tokens = await login(email, password);
    const connection = await createConnection(tokens.access_token);
    await setStoredConnection(connection.id, connection.push_token);

    statusEl.textContent = "Connected! You can close this tab and use the extension popup to sync.";
    statusEl.className = "success";
    form.hidden = true;
  } catch (err) {
    statusEl.textContent = err.message;
    statusEl.className = "error";
  }
});

showExistingConnection();
