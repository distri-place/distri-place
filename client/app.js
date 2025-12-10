(() => {
    const userId = crypto.randomUUID();
    const connectBtn = document.getElementById("connect");
    const colorInput = document.getElementById("color");
    const canvas = document.getElementById("board");
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    const statusEl = document.getElementById("status");
    const statusDot = document.getElementById("statusDot");
    const colorSwatches = document.querySelectorAll(".color-swatch");

    const PING_INTERVAL = 5000;
    const RECONNECT_DELAY = 500;
    const PATIENCE = 3000;
    const SCALE = 12;

    let W = 64,
        H = 64;
    let currentColor = "#ff0000";
    let connectedNode = null;

    canvas.width = W;
    canvas.height = H;
    canvas.style.width = canvas.width * SCALE + "px";
    canvas.style.height = canvas.height * SCALE + "px";

    let ws = null;
    let isConnected = false;
    let pending = new Map();

    function setIsConnected(v) {
        if (v === isConnected) return;
        isConnected = v;
        connectBtn.textContent = v ? "Disconnect" : "Connect";
        statusDot.className = `status-dot ${v ? "connected" : ""}`;
        if (!v) {
            connectedNode = null;
            setStatus("disconnected");
        }
    }

    function setStatus(text) {
        statusEl.textContent = text;
    }

    async function setPixel(x, y, color) {
        const key = `${x},${y}`;
        setPixelLocal(x, y, color);
        pending.set(key, color);

        if (!isConnected) connect().then();

        try {
            const response = await fetch("http://localhost:8080/client/pixel", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId, x, y, color }),
            });

            if (response.ok) pending.delete(key);
            else setTimeout(() => revertPixel(x, y), 100);
        } catch (error) {
            setTimeout(() => revertPixel(x, y), 100);
        }
    }

    function revertPixel(x, y) {
        pending.delete(`${x},${y}`);
        setPixelLocal(x, y, 0);
    }

    function setPixelLocal(x, y, color) {
        const img = ctx.getImageData(x, y, 1, 1);
        img.data[0] = (color >> 16) & 255;
        img.data[1] = (color >> 8) & 255;
        img.data[2] = color & 255;
        img.data[3] = 255;
        ctx.putImageData(img, x, y);
    }

    async function loadInitialCanvas() {
        try {
            const response = await fetch("http://localhost:8080/client/pixels");
            const data = await response.json();
            const pixels = data.pixels;

            ctx.fillStyle = "#000000";
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            for (let y = 0; y < H; y++) {
                for (let x = 0; x < W; x++) {
                    const pixelIndex = y * W + x;
                    const color = pixels[pixelIndex];
                    if (color !== 0) {
                        setPixelLocal(x, y, color);
                    }
                }
            }
        } catch (error) {
            console.error("Error loading canvas:", error);
        }
    }

    function pickPixel(x, y) {
        const data = ctx.getImageData(x, y, 1, 1).data;
        const color =
            "#" +
            ((data[0] << 16) | (data[1] << 8) | data[2])
                .toString(16)
                .padStart(6, "0");
        selectColor(color);
    }

    function selectColor(color) {
        currentColor = color;
        colorInput.value = color;
        colorSwatches.forEach((s) => s.classList.remove("selected"));
        const swatch = document.querySelector(`[data-color="${color}"]`);
        if (swatch) swatch.classList.add("selected");
    }

    function canvasXY(evt) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;

        const cx = Math.floor((evt.clientX - rect.left) * scaleX);
        const cy = Math.floor((evt.clientY - rect.top) * scaleY);

        return [
            Math.max(0, Math.min(cx, W - 1)),
            Math.max(0, Math.min(cy, H - 1)),
        ];
    }

    canvas.addEventListener("click", (evt) => {
        const [x, y] = canvasXY(evt);
        if (evt.shiftKey) {
            pickPixel(x, y);
        } else {
            const hexColor = currentColor.replace("#", "");
            const intColor = parseInt(hexColor, 16) || 0;
            setPixel(x, y, intColor);
        }
    });

    colorSwatches.forEach((swatch) => {
        swatch.addEventListener("click", () => {
            selectColor(swatch.dataset.color);
        });
    });

    function connect() {
        return new Promise((resolve) => {
            disconnect();
            ws = new WebSocket("ws://localhost:8080/ws/");
            setStatus("connecting…");

            let timeout = undefined;

            function ping() {
                ws.send(JSON.stringify({ type: "ping" }));
                timeout = setTimeout(disconnect, PATIENCE);
            }

            ws.onopen = () => {
                setIsConnected(true);
                timeout = setTimeout(ping, PING_INTERVAL);
                resolve(ws);
                ws.send(
                    JSON.stringify({
                        type: "connect",
                        content: { user_id: userId },
                    })
                );
            };

            ws.onclose = () => {
                setIsConnected(false);
                setStatus("disconnected");
                clearTimeout(timeout);
            };

            ws.onerror = () => setStatus("error (see console)");

            ws.onmessage = (ev) => {
                clearTimeout(timeout);
                timeout = setTimeout(ping, PING_INTERVAL);

                let msg;
                try {
                    msg = JSON.parse(ev.data);
                } catch (e) {
                    setStatus(`error: invalid message, message=${ev.data}`);
                    return;
                }

                switch (msg.type) {
                    case "error":
                        setStatus(`error: ${msg.message || "?"}`);
                        return;
                    case "connected":
                        const { id: nodeId } = msg.content.node;
                        connectedNode = nodeId;
                        setStatus(`node ${nodeId}`);
                        loadInitialCanvas();
                        return;
                    case "pixel":
                        const { x, y, color } = msg.content;
                        const key = `${x},${y}`;
                        if (!pending.has(key)) {
                            setPixelLocal(x, y, color);
                        } else if (pending.get(key) === color) {
                            pending.delete(key);
                        }
                        return;
                    case "pong":
                        return;
                    default:
                        setStatus(`error: unknown message type "${msg.type}"`);
                        return;
                }
            };
        });
    }

    function disconnect(reconnect = false) {
        if (ws) {
            ws.close();
            ws = null;
        }
        setIsConnected(false);
        if (reconnect) setTimeout(connect, RECONNECT_DELAY);
    }

    selectColor("#ff0000");
    connect();

    connectBtn.addEventListener("click", () => {
        if (isConnected) disconnect();
        else connect();
    });
})();
