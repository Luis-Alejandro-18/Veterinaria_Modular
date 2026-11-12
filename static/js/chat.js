/* Chat con polling: envía y recibe mensajes sin recargar la página. */
(function () {
  'use strict';

  var cont = document.getElementById('chat-messages');
  if (!cont) return;

  var form = document.getElementById('chat-form');
  var status = document.getElementById('chat-status');
  var nuevoBtn = document.getElementById('chat-nuevos');
  var textarea = form ? form.querySelector('textarea[name="mensaje"]') : null;

  var endpoint = cont.dataset.endpoint;
  var enviarUrl = cont.dataset.enviar;
  var leidoUrl = cont.dataset.leido;
  var estilo = cont.dataset.estilo || 'dueno';
  var rol = cont.dataset.rol || '';
  var intervalo = 2500;

  var ultimoId = parseInt(cont.dataset.desdeId || '0', 10) || 0;
  var enviando = false;
  var cargando = false;
  var leidoHecho = false;

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
  }

  function setStatus(texto, tipo) {
    if (!status) return;
    status.textContent = texto;
    if (tipo) status.dataset.estado = tipo;
  }

  function cercaDelFinal() {
    return cont.scrollHeight - cont.scrollTop - cont.clientHeight < 80;
  }

  function ocultarNuevos() {
    if (nuevoBtn) nuevoBtn.hidden = true;
  }

  function mostrarNuevos() {
    if (nuevoBtn) nuevoBtn.hidden = false;
  }

  function alFinal() {
    cont.scrollTop = cont.scrollHeight;
    ocultarNuevos();
  }

  function quitarVacio() {
    var vacio = document.getElementById('chat-empty');
    if (vacio) vacio.remove();
  }

  function crearMensaje(mensaje) {
    var div = document.createElement('div');
    if (estilo === 'vet') {
      div.className = 'vet-msg' + (mensaje.es_propio ? ' own' : '');
      var meta = document.createElement('div');
      meta.className = 'vet-msg-meta';
      var nombre = document.createElement('span');
      nombre.textContent = mensaje.remitente;
      var sep = document.createElement('span');
      sep.textContent = '·';
      sep.setAttribute('aria-hidden', 'true');
      var hora = document.createElement('span');
      hora.textContent = mensaje.fecha_hora;
      meta.append(nombre, sep, hora);
      var cuerpoVet = document.createElement('div');
      cuerpoVet.className = 'vet-msg-body';
      cuerpoVet.textContent = mensaje.texto;
      div.append(meta, cuerpoVet);
    } else {
      div.className = 'chat-message ' + (mensaje.es_propio ? 'chat-message-own' : 'chat-message-theirs');
      var remitente = document.createElement('div');
      remitente.className = 'chat-message-sender';
      remitente.textContent = mensaje.remitente + ' ';
      var horaDueno = document.createElement('small');
      horaDueno.textContent = mensaje.hora;
      remitente.append(horaDueno);
      var cuerpoDueno = document.createElement('div');
      cuerpoDueno.className = 'chat-message-body';
      cuerpoDueno.textContent = mensaje.texto;
      div.append(remitente, cuerpoDueno);
    }
    if (mensaje.id !== undefined && mensaje.id !== null) {
      div.dataset.id = String(mensaje.id);
    }
    return div;
  }

  function agregar(mensaje) {
    if (mensaje.id !== undefined && mensaje.id !== null &&
        cont.querySelector('[data-id="' + mensaje.id + '"]')) {
      return false;
    }
    quitarVacio();
    var estabaAbajo = cercaDelFinal();
    cont.appendChild(crearMensaje(mensaje));
    if (estabaAbajo) alFinal(); else mostrarNuevos();
    return true;
  }

  function horaLocal(fecha) {
    return new Intl.DateTimeFormat('es-MX', {
      hour: '2-digit', minute: '2-digit', hour12: false
    }).format(fecha);
  }

  function fechaHoraLocal(fecha) {
    var texto = new Intl.DateTimeFormat('es-MX', {
      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false
    }).format(fecha);
    return texto.replace(',', '');
  }

  function notaCerrada() {
    if (document.getElementById('chat-cerrado') || !form) return;
    var nota = document.createElement('p');
    nota.id = 'chat-cerrado';
    nota.className = 'hint';
    nota.textContent = 'La consulta está cerrada. Ya no se pueden enviar mensajes.';
    form.replaceWith(nota);
  }

  function actualizarEstado(data) {
    if (data && data.puede_escribir === false) {
      if (form) form.hidden = true;
      notaCerrada();
    }
  }

  async function marcarLeido() {
    if (rol !== 'veterinario' || !leidoUrl) return;
    try {
      await fetch(leidoUrl, {
        method: 'POST',
        headers: {'X-CSRFToken': csrfToken(), 'Accept': 'application/json'}
      });
    } catch (error) {
      /* Silencioso: el contador se actualiza en la siguiente visita. */
    }
  }

  async function pedirNuevos() {
    if (cargando || document.hidden) return;
    cargando = true;
    try {
      var respuesta = await fetch(endpoint + '?desde_id=' + encodeURIComponent(ultimoId), {
        headers: {'Accept': 'application/json'}
      });
      if (respuesta.status === 401) {
        setStatus('Tu sesión expiró. Recarga la página.', 'error');
        return;
      }
      if (!respuesta.ok) throw new Error('Error ' + respuesta.status);

      var data = await respuesta.json();
      var nuevos = data.mensajes || [];
      var agregados = 0;
      for (var i = 0; i < nuevos.length; i += 1) {
        if (agregar(nuevos[i])) agregados += 1;
        if (nuevos[i].id > ultimoId) ultimoId = nuevos[i].id;
      }
      if (data.ultimo_id > ultimoId) ultimoId = data.ultimo_id;

      actualizarEstado(data);
      setStatus('En línea', 'ok');
      if (rol === 'veterinario' && (agregados > 0 || !leidoHecho)) {
        leidoHecho = true;
        marcarLeido();
      }
    } catch (error) {
      setStatus('Sin conexión. Reintentando…', 'error');
    } finally {
      cargando = false;
    }
  }

  async function enviar(evento) {
    evento.preventDefault();
    if (enviando || !textarea) return;
    var texto = textarea.value.trim();
    if (!texto) {
      textarea.focus();
      return;
    }

    enviando = true;
    var boton = form.querySelector('button[type="submit"]');
    if (boton) boton.disabled = true;

    var ahora = new Date();
    var temporal = {
      id: null,
      texto: texto,
      remitente: 'Tú',
      es_propio: true,
      hora: horaLocal(ahora),
      fecha_hora: fechaHoraLocal(ahora)
    };
    var nodoTemporal = crearMensaje(temporal);
    quitarVacio();
    cont.appendChild(nodoTemporal);
    alFinal();
    textarea.value = '';

    try {
      var respuesta = await fetch(enviarUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken(),
          'Accept': 'application/json'
        },
        body: JSON.stringify({mensaje: texto})
      });
      if (!respuesta.ok) {
        var errorData = await respuesta.json().catch(function () { return {}; });
        throw new Error(errorData.error || 'No se pudo enviar el mensaje.');
      }
      var data = await respuesta.json();
      nodoTemporal.remove();
      agregar(data.mensaje);
      if (data.mensaje.id > ultimoId) ultimoId = data.mensaje.id;
      actualizarEstado(data);
      setStatus('En línea', 'ok');
    } catch (error) {
      nodoTemporal.remove();
      if (!textarea.value) textarea.value = texto;
      setStatus(error.message, 'error');
    } finally {
      enviando = false;
      if (boton) boton.disabled = false;
      textarea.focus();
    }
  }

  if (nuevoBtn) nuevoBtn.addEventListener('click', alFinal);
  cont.addEventListener('scroll', function () {
    if (cercaDelFinal()) ocultarNuevos();
  });
  if (form) form.addEventListener('submit', enviar);
  if (textarea) {
    textarea.addEventListener('keydown', function (evento) {
      if (evento.key === 'Enter' && !evento.shiftKey) {
        evento.preventDefault();
        if (form.requestSubmit) form.requestSubmit();
        else form.dispatchEvent(new Event('submit', {cancelable: true}));
      }
    });
  }

  alFinal();
  setStatus('Conectando…', '');
  pedirNuevos();
  setInterval(pedirNuevos, intervalo);
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) pedirNuevos();
  });
})();
