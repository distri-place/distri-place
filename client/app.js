(() => {
    const userId = crypto.randomUUID();
    const connectBtn = document.getElementById('connect');
    const colorInput = document.getElementById('color');
    const canvas = document.getElementById('board');
    const ctx = canvas.getContext('2d', {willReadFrequently: true});
    const statusEl = document.getElementById('status');
    const logEl = document.getElementById('log');
    const PING_INTERVAL = 5000;
    const RECONNECT_DELAY = 500;
    const PATIENCE = 3000;

    const SCALE = 8;
    canvas.style.width = (canvas.width * SCALE) + 'px';
    canvas.style.height = (canvas.height * SCALE) + 'px';

    let ws = null;
    let W = 64, H = 64;
    let isConnected = false;

    function setIsConnected(v) {
        if (v === isConnected) return;
        isConnected = v;
        setStatus(v ? 'connected' : 'disconnected');
        connectBtn.textContent = v ? 'Disconnect' : 'Connect';
    }

    function appendLog(text) {
        const p = document.createElement('div');
        p.textContent = text;
        logEl.appendChild(p);
        logEl.scrollTop = logEl.scrollHeight;
    }

    function setStatus(text) {
        statusEl.textContent = text;
        appendLog(text);
    }


    async function setPixel(x, y, color) {
        if (!isConnected) connect().then()
        await fetch("http://localhost:8080/client/pixel", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                user_id: userId,
                x: x,
                y: y,
                color: color
            })
        });
    }


    function setPixelLocal(x, y, color) {
        const img = ctx.getImageData(x, y, 1, 1);
        img.data[0] = (color >> 16) & 255;
        img.data[1] = (color >> 8) & 255;
        img.data[2] = color & 255;
        img.data[3] = 255;
        ctx.putImageData(img, x, y);
    }

    function pickPixel(x, y) {
        const data = ctx.getImageData(x, y, 1, 1).data;
        const color = (data[0] << 16) | (data[1] << 8) | data[2];
        colorInput.value = '#' + color.toString(16).padStart(6, '0');
    }

    function canvasXY(evt) {
        const rect = canvas.getBoundingClientRect();
        const cx = Math.floor((evt.clientX - rect.left) / (rect.width / W));
        const cy = Math.floor((evt.clientY - rect.top) / (rect.height / H));
        return [Math.max(0, Math.min(W - 1, cx)), Math.max(0, Math.min(H - 1, cy))];
    }

    canvas.addEventListener('click', (evt) => {
        const [x, y] = canvasXY(evt);
        if (evt.shiftKey) pickPixel(x, y);
        else {
            const hexColor = colorInput.value.replace('#', '');
            const intColor = parseInt(hexColor, 16) || 0;
            setPixel(x, y, intColor);
        }
    });

    function connect() {
        return new Promise((resolve) => {
            disconnect()
            ws = new WebSocket("ws://localhost:8080/ws/");
            setStatus('connecting…');

            let timeout = undefined;

            function ping() {
                ws.send(JSON.stringify({type: 'ping'}));
                appendLog('ping ->');
                timeout = setTimeout(disconnect, PATIENCE);
            }

            ws.onopen = () => {
                setIsConnected(true)
                timeout = setTimeout(ping, PING_INTERVAL);
                resolve(ws)
                ws.send(JSON.stringify({
                    type: 'connect',
                    content: { user_id: userId }
                }))
            };

            ws.onclose = () => {
                setIsConnected(false)
                setStatus('disconnected');
                clearTimeout(timeout);
            };

            ws.onerror = () => setStatus('error (see console)');

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
                    case 'error':
                        setStatus(`error: ${msg.message || '?'}`);
                        return;
                    case 'connected':
                        const canvasData = msg.content.canvas;
                        const { id: nodeId, role } = msg.content.node;
                        appendLog(`<- connected: node=${nodeId} (${role})`);
                        const img = new Image();
                        img.onload = () => ctx.drawImage(img, 0, 0)
                        img.src = "data:image/png;base64," + canvasData
                        return;
                    case 'pixel':
                        const {x, y, color, user_id} = msg.content;
                        appendLog(`<- pixel set: (${x}, ${y}) = ${color} by ${user_id}${user_id === userId ? ' (you)' : ''}`);
                        setPixelLocal(x, y, color);
                        return;
                    case 'pong':
                        appendLog('<- pong');
                        return;
                    default:
                        setStatus(`error: unknown message type "${msg.type}"`);
                        return;
                }
            }
        })

    }

    function disconnect(reconnect = false) {
        if (ws) {
            ws.close();
            ws = null;
        }
        setIsConnected(false);
        if (reconnect) setTimeout(connect, RECONNECT_DELAY);
    }

    connect()

    connectBtn.addEventListener('click', () => {
        if (isConnected) disconnect()
        else connect();

    });
})();
