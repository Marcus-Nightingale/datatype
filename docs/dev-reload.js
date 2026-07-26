(() => {
  const localHosts = new Set(['localhost', '127.0.0.1']);
  if (!localHosts.has(window.location.hostname) || window.location.port !== '8080') {
    return;
  }

  function connect() {
    const socket = new WebSocket(`ws://${window.location.hostname}:8081`);

    socket.addEventListener('message', event => {
      const message = JSON.parse(event.data);
      if (message.type === 'reload') window.location.reload();
    });

    socket.addEventListener('close', () => {
      window.setTimeout(connect, 2000);
    });
  }

  connect();
})();
