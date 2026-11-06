(function () {
  "use strict";

  var STORAGE_KEY = "rrhh-asistencia-demo-v1";
  var state = {
    mode: "demo",
    db: null,
    auth: null,
    currentUser: null,
    employees: [],
    balances: {},
    movements: [],
    attendance: [],
    filteredEmployeeId: null
  };

  var demoSeed = {
    employees: [
      { id: "demo-ana", nombre: "Ana Pérez" },
      { id: "demo-marcos", nombre: "Marcos Ruiz" },
      { id: "demo-lucia", nombre: "Lucía Torres" },
      { id: "demo-diego", nombre: "Diego López" }
    ],
    balances: {
      "demo-ana": 6.5,
      "demo-marcos": 3,
      "demo-lucia": 0,
      "demo-diego": 8.25
    },
    movements: [
      { id: "demo-m1", empleadoId: "demo-ana", empleadoNombre: "Ana Pérez", tipo: "ACUMULACION", horas: 8.5, saldoResultante: 8.5, detalle: "Horas extra", fecha: "2026-10-28T10:30:00" },
      { id: "demo-m2", empleadoId: "demo-ana", empleadoNombre: "Ana Pérez", tipo: "DEVOLUCION", horas: 2, saldoResultante: 6.5, detalle: "Compensación", fecha: "2026-10-30T09:00:00" },
      { id: "demo-m3", empleadoId: "demo-marcos", empleadoNombre: "Marcos Ruiz", tipo: "ACUMULACION", horas: 3, saldoResultante: 3, detalle: "Cobertura de turno", fecha: "2026-10-31T15:15:00" },
      { id: "demo-m4", empleadoId: "demo-diego", empleadoNombre: "Diego López", tipo: "ACUMULACION", horas: 8.25, saldoResultante: 8.25, detalle: "Horas extra", fecha: "2026-11-01T12:00:00" }
    ],
    attendance: []
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function showMessage(element, message, isError) {
    element.textContent = message || "";
    element.classList.toggle("error", Boolean(isError));
    element.classList.toggle("success", Boolean(message) && !isError);
  }

  function setScreen(showApp) {
    byId("access-screen").classList.toggle("hidden", showApp);
    byId("app-screen").classList.toggle("hidden", !showApp);
  }

  function showApplication(userLabel) {
    setScreen(true);
    byId("user-display").textContent = userLabel || "";
    byId("mode-badge").textContent = state.mode === "demo" ? "DEMO LOCAL" : ((state.currentUser && state.currentUser.rol) || "FIRESTORE API");
    byId("mode-badge").classList.toggle("demo-badge", state.mode === "demo");
    var canManage = state.mode === "demo" || (state.currentUser && state.currentUser.rol === "SUPERADMIN");
    ["attendance-form", "employee-form", "movement-form"].forEach(function (formId) {
      byId(formId).classList.toggle("hidden", !canManage);
    });
    render();
  }

  function deepCopy(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function loadDemoState() {
    try {
      var saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved) {
        var parsed = JSON.parse(saved);
        if (parsed && Array.isArray(parsed.employees) && parsed.balances && Array.isArray(parsed.movements)) {
          return parsed;
        }
      }
    } catch (error) {
      console.warn("No se pudo leer el estado local de la demo.", error);
    }
    return deepCopy(demoSeed);
  }

  function saveDemoState() {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({
      employees: state.employees,
      balances: state.balances,
      movements: state.movements,
      attendance: state.attendance
    }));
  }

  function initialize() {
    byId("attendance-date").value = new Date().toISOString().slice(0, 10);
    bindEvents();

    if (window.firebase && window.firebase.apps && window.firebase.apps.length > 0) {
      initializeBackendMode();
    } else {
      byId("login-form").classList.add("hidden");
      byId("login-error").textContent = "Firebase no está configurado. Podés entrar a la demo sin datos reales.";
    }
  }

  function bindEvents() {
    byId("demo-button").addEventListener("click", enterDemo);
    byId("login-form").addEventListener("submit", signIn);
    byId("logout-button").addEventListener("click", signOut);
    byId("employee-form").addEventListener("submit", createEmployee);
    byId("movement-form").addEventListener("submit", registerMovement);
    byId("attendance-form").addEventListener("submit", registerAttendance);
    byId("show-all-movements").addEventListener("click", function () {
      state.filteredEmployeeId = null;
      renderMovements();
    });

    document.querySelectorAll(".nav-button").forEach(function (button) {
      button.addEventListener("click", function () {
        document.querySelectorAll(".nav-button").forEach(function (item) {
          item.classList.toggle("active", item === button);
        });
        document.querySelectorAll(".panel").forEach(function (panel) {
          panel.classList.toggle("hidden", panel.id !== button.dataset.target);
        });
      });
    });
  }

  function initializeBackendMode() {
    state.mode = "flask";
    try {
      state.auth = window.firebase.auth();
      state.db = null;
      byId("login-form").classList.remove("hidden");
      byId("login-error").textContent = "";
      state.auth.onAuthStateChanged(function (user) {
        if (!user) {
          state.currentUser = null;
          setScreen(false);
          return;
        }
        loadBackendUser().then(function () {
          return loadBackendState();
        }).then(function () {
          showApplication((state.currentUser && state.currentUser.nombre) || user.email || "Usuario autenticado");
        }).catch(function (error) {
          setScreen(false);
          showMessage(byId("login-error"), "No se pudo validar el acceso al backend: " + error.message, true);
          state.auth.signOut();
        });
      });
      fetchJson("/api/health").catch(function () {
        showMessage(byId("login-error"), "El backend Flask no está disponible. Podés usar la demo sin datos reales.", true);
      });
    } catch (error) {
      state.mode = "demo";
      byId("login-form").classList.add("hidden");
      byId("login-error").textContent = "Firebase no está configurado. Podés entrar a la demo sin datos reales.";
    }
  }

  function buildApiHeaders(extraHeaders) {
    var headers = Object.assign({}, extraHeaders || {});
    var user = state.auth && state.auth.currentUser;
    if (!user) {
      return Promise.resolve(headers);
    }
    return user.getIdToken().then(function (token) {
      headers.Authorization = "Bearer " + token;
      return headers;
    });
  }

  function fetchJson(path, options) {
    var requestOptions = Object.assign({}, options || {});
    return buildApiHeaders(requestOptions.headers).then(function (headers) {
      requestOptions.headers = headers;
      return fetch(path, requestOptions);
    }).then(function (response) {
      var contentType = response.headers.get("content-type") || "";
      var payloadPromise = contentType.indexOf("application/json") !== -1 ? response.json() : response.text();
      return payloadPromise.then(function (payload) {
        if (!response.ok) {
          var message = payload && typeof payload === "object" ? (payload.error || payload.message) : payload;
          throw new Error(message || "Error del backend (" + response.status + ").");
        }
        return payload;
      });
    });
  }

  function loadBackendUser() {
    return fetchJson("/api/auth/me").then(function (user) {
      state.currentUser = user;
    });
  }

  function signIn(event) {
    event.preventDefault();
    if (!state.auth) {
      showMessage(byId("login-error"), "Firebase no está configurado; usá la demo pública.", true);
      return;
    }
    state.auth.signInWithEmailAndPassword(byId("email").value.trim(), byId("password").value)
      .catch(function (error) {
        showMessage(byId("login-error"), "No se pudo iniciar sesión: " + error.message, true);
      });
  }

  function signOut() {
    if (state.auth && state.auth.currentUser) {
      state.auth.signOut();
    } else {
      state.currentUser = null;
      setScreen(false);
    }
  }

  function enterDemo() {
    state.mode = "demo";
    state.db = null;
    state.auth = null;
    state.currentUser = null;
    var data = loadDemoState();
    state.employees = data.employees;
    state.balances = data.balances;
    state.movements = data.movements;
    state.attendance = data.attendance || [];
    state.filteredEmployeeId = null;
    showApplication("Demo pública");
  }

  function loadBackendState() {
    return Promise.all([
      fetchJson("/api/employees"),
      fetchJson("/api/movements"),
      fetchJson("/api/attendance")
    ]).then(function (results) {
      var employees = Array.isArray(results[0]) ? results[0] : [];
      var movements = Array.isArray(results[1]) ? results[1] : [];
      var attendance = Array.isArray(results[2]) ? results[2] : [];
      state.employees = employees.map(function (employee) {
        return { id: employee.id, nombre: employee.nombre };
      });
      state.balances = {};
      employees.forEach(function (employee) {
        state.balances[employee.id] = Number(employee.saldo_horas || 0);
      });
      state.movements = movements.map(function (movement) {
        return {
          id: movement.id,
          empleadoId: movement.empleado_id,
          empleadoNombre: movement.empleado_nombre,
          tipo: movement.tipo,
          horas: Number(movement.horas || 0),
          saldoResultante: Number(movement.saldo_resultante || 0),
          detalle: movement.detalle || "",
          fecha: movement.fecha || ""
        };
      });
      state.attendance = attendance.map(function (entry) {
        return {
          id: entry.id,
          empleadoId: entry.empleado_id,
          empleadoNombre: entry.empleado_nombre,
          estado: entry.estado,
          fecha: entry.fecha || ""
        };
      });
      state.filteredEmployeeId = null;
    });
  }

  function render() {
    renderEmployeeSelectors();
    renderSummary();
    renderBalances();
    renderMovements();
  }

  function renderEmployeeSelectors() {
    ["attendance-employee", "movement-employee"].forEach(function (selectId) {
      var select = byId(selectId);
      var previous = select.value;
      select.replaceChildren();
      var placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = state.employees.length ? "Seleccioná un empleado" : "Primero agregá un empleado";
      select.appendChild(placeholder);
      state.employees.forEach(function (employee) {
        var option = document.createElement("option");
        option.value = employee.id;
        option.textContent = employee.nombre;
        select.appendChild(option);
      });
      if (state.employees.some(function (employee) { return employee.id === previous; })) {
        select.value = previous;
      }
    });
  }

  function renderSummary() {
    var total = state.employees.reduce(function (sum, employee) {
      return sum + Number(state.balances[employee.id] || 0);
    }, 0);
    byId("employee-count").textContent = String(state.employees.length);
    byId("total-hours").textContent = formatHours(total);
  }

  function renderBalances() {
    var body = byId("balances-body");
    body.replaceChildren();
    byId("empty-employees").classList.toggle("hidden", state.employees.length > 0);

    state.employees.forEach(function (employee) {
      var row = document.createElement("tr");
      var name = document.createElement("td");
      name.textContent = employee.nombre;
      var balance = document.createElement("td");
      balance.className = "balance-cell";
      balance.textContent = formatHours(state.balances[employee.id] || 0);
      var action = document.createElement("td");
      var button = document.createElement("button");
      button.type = "button";
      button.className = "text-button";
      button.textContent = "Ver movimientos";
      button.addEventListener("click", function () {
        state.filteredEmployeeId = employee.id;
        byId("movement-heading").textContent = "Movimientos de " + employee.nombre;
        renderMovements();
      });
      action.appendChild(button);
      row.append(name, balance, action);
      body.appendChild(row);
    });
  }

  function renderMovements() {
    var body = byId("movements-body");
    body.replaceChildren();
    var employeeById = {};
    state.employees.forEach(function (employee) { employeeById[employee.id] = employee; });
    var items = state.movements.filter(function (movement) {
      return !state.filteredEmployeeId || movement.empleadoId === state.filteredEmployeeId;
    });
    items.sort(function (left, right) {
      return new Date(right.fecha).getTime() - new Date(left.fecha).getTime();
    });
    byId("empty-movements").classList.toggle("hidden", items.length > 0);
    byId("show-all-movements").classList.toggle("hidden", !state.filteredEmployeeId);
    if (!state.filteredEmployeeId) {
      byId("movement-heading").textContent = "Movimientos recientes";
    }

    items.forEach(function (movement) {
      var row = document.createElement("tr");
      var date = document.createElement("td");
      date.textContent = formatDate(movement.fecha);
      var name = document.createElement("td");
      name.textContent = movement.empleadoNombre || (employeeById[movement.empleadoId] || {}).nombre || "Empleado";
      var type = document.createElement("td");
      type.textContent = movement.tipo === "DEVOLUCION" ? "Devolución" : "Acumulación";
      type.className = movement.tipo === "DEVOLUCION" ? "movement-return" : "movement-add";
      var hours = document.createElement("td");
      hours.textContent = (movement.tipo === "DEVOLUCION" ? "−" : "+") + formatHours(movement.horas);
      var balance = document.createElement("td");
      balance.textContent = formatHours(movement.saldoResultante);
      var note = document.createElement("td");
      note.textContent = movement.detalle || "—";
      row.append(date, name, type, hours, balance, note);
      body.appendChild(row);
    });
  }

  function createEmployee(event) {
    event.preventDefault();
    var nameInput = byId("employee-name");
    var name = nameInput.value.trim();
    if (!name) {
      showMessage(byId("hours-message"), "Escribí el nombre del empleado.", true);
      return;
    }

    if (state.mode === "demo") {
      var demoEmployee = { id: "demo-" + Date.now(), nombre: name };
      state.employees.push(demoEmployee);
      state.balances[demoEmployee.id] = 0;
      saveDemoState();
      nameInput.value = "";
      render();
      showMessage(byId("hours-message"), "Empleado agregado con saldo inicial de 0,00 horas.");
      return;
    }

    fetchJson("/api/employees", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre: name })
    }).then(function () {
      nameInput.value = "";
      return loadBackendState();
    }).then(render).then(function () {
      showMessage(byId("hours-message"), "Empleado agregado con saldo inicial de 0,00 horas.");
    }).catch(function (error) {
      showMessage(byId("hours-message"), "No se pudo agregar el empleado: " + error.message, true);
    });
  }

  function registerMovement(event) {
    event.preventDefault();
    var kind = event.submitter ? event.submitter.dataset.kind : "ACUMULACION";
    var employeeId = byId("movement-employee").value;
    var hours = Number(byId("movement-hours").value);
    var detail = byId("movement-note").value.trim();
    var employee = state.employees.find(function (item) { return item.id === employeeId; });

    if (!employee) {
      showMessage(byId("hours-message"), "Seleccioná un empleado.", true);
      return;
    }
    if (!Number.isFinite(hours) || hours <= 0 || Math.round(hours * 100) !== hours * 100) {
      showMessage(byId("hours-message"), "Ingresá una cantidad positiva con hasta dos decimales.", true);
      return;
    }

    if (state.mode === "demo") {
      var current = Number(state.balances[employeeId] || 0);
      var next = kind === "ACUMULACION" ? current + hours : current - hours;
      if (next < 0) {
        showMessage(byId("hours-message"), "La devolución supera las horas disponibles.", true);
        return;
      }
      state.balances[employeeId] = roundHours(next);
      state.movements.unshift({
        id: "demo-" + Date.now(),
        empleadoId: employeeId,
        empleadoNombre: employee.nombre,
        tipo: kind,
        horas: hours,
        saldoResultante: state.balances[employeeId],
        detalle: detail,
        fecha: new Date().toISOString()
      });
      saveDemoState();
      byId("movement-hours").value = "";
      byId("movement-note").value = "";
      render();
      showMessage(byId("hours-message"), kind === "DEVOLUCION" ? "Devolución registrada y descontada del saldo." : "Horas acumuladas correctamente.");
      return;
    }

    fetchJson("/api/movements", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        empleado_id: employeeId,
        tipo: kind,
        horas: hours,
        detalle: detail
      })
    }).then(function () {
      byId("movement-hours").value = "";
      byId("movement-note").value = "";
      return loadBackendState();
    }).then(render).then(function () {
      showMessage(byId("hours-message"), kind === "DEVOLUCION" ? "Devolución registrada y descontada del saldo." : "Horas acumuladas correctamente.");
    }).catch(function (error) {
      showMessage(byId("hours-message"), error.message || "No se pudo registrar el movimiento.", true);
    });
  }

  function registerAttendance(event) {
    event.preventDefault();
    var employeeId = byId("attendance-employee").value;
    var employee = state.employees.find(function (item) { return item.id === employeeId; });
    if (!employee) {
      showMessage(byId("attendance-message"), "Seleccioná un empleado.", true);
      return;
    }

    var entry = {
      empleadoId: employee.id,
      empleadoNombre: employee.nombre,
      estado: byId("attendance-status").value,
      fecha: byId("attendance-date").value
    };

    if (state.mode === "demo") {
      entry.id = "demo-a-" + Date.now();
      state.attendance.unshift(entry);
      saveDemoState();
      showMessage(byId("attendance-message"), "Asistencia guardada en esta demo para " + employee.nombre + ".");
      return;
    }

    fetchJson("/api/attendance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        empleado_id: employee.id,
        estado: entry.estado,
        fecha: entry.fecha
      })
    }).then(function () {
      showMessage(byId("attendance-message"), "Asistencia guardada para " + employee.nombre + ".");
    }).catch(function (error) {
      showMessage(byId("attendance-message"), "No se pudo guardar la asistencia: " + error.message, true);
    });
  }

  function formatHours(value) {
    return Number(value || 0).toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " h";
  }

  function roundHours(value) {
    return Math.round((Number(value) + Number.EPSILON) * 100) / 100;
  }

  function formatDate(value) {
    var date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "—";
    }
    return new Intl.DateTimeFormat("es-AR", { dateStyle: "short", timeStyle: "short" }).format(date);
  }

  document.addEventListener("DOMContentLoaded", initialize);
}());
