import logging
import socket
import threading

logger = logging.getLogger(__name__)


def handle_websocket_upgrade(request_handler, load_balancer):
    try:
        backend = load_balancer.get_next_backend()
        backend_host, backend_port = backend.split(":")
        backend_port = int(backend_port)

        backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        backend_socket.connect((backend_host, backend_port))

        request_line = f"{request_handler.command} {request_handler.path} {request_handler.request_version}\r\n"
        backend_socket.send(request_line.encode())

        for header, value in request_handler.headers.items():
            header_line = f"{header}: {value}\r\n"
            backend_socket.send(header_line.encode())
        backend_socket.send(b"\r\n")

        response_data = b""
        while True:
            chunk = backend_socket.recv(1024)
            if not chunk:
                break
            response_data += chunk
            if b"\r\n\r\n" in response_data:
                break

        request_handler.wfile.write(response_data)
        request_handler.wfile.flush()

        client_socket = request_handler.connection

        def forward_data(source, destination):
            try:
                while True:
                    data = source.recv(4096)
                    if not data:
                        break
                    destination.send(data)
            except:
                pass
            finally:
                try:
                    source.close()
                    destination.close()
                except:
                    pass

        t1 = threading.Thread(
            target=forward_data, args=(client_socket, backend_socket), daemon=True
        )
        t2 = threading.Thread(
            target=forward_data, args=(backend_socket, client_socket), daemon=True
        )
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    except Exception as e:
        try:
            request_handler.send_error(502, f"WebSocket upgrade failed: {str(e)}")
        except:
            pass