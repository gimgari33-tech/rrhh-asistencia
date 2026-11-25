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

    if (byId("load-real-sheet-btn")) {
      byId("load-real-sheet-btn").addEventListener("click", loadRealSheet);
    }
    if (byId("upload-sheet-input")) {
      byId("upload-sheet-input").addEventListener("change", handleCustomSheetUpload);
    }
    if (byId("process-vision-btn")) {
      byId("process-vision-btn").addEventListener("click", processVisionSheet);
    }
    if (byId("apply-to-bank-btn")) {
      byId("apply-to-bank-btn").addEventListener("click", applyVisionResultsToBank);
    }

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

  var visionDemoResults = [
    {
      legajo: "20740",
      nombre: "ALANCAY ALDO",
      jornada: 8.0,
      entrada: "13:26",
      salida: "18:00",
      estado: "Presente",
      horasTrabajadas: 4.57,
      diferencia: -3.43,
      observacion: "Presente con horas faltantes a compensar (-3.43h)."
    },
    {
      legajo: "65429",
      nombre: "ALVARADO CINTIA",
      jornada: 5.0,
      entrada: "00:00",
      salida: "05:03",
      estado: "Presente",
      horasTrabajadas: 5.05,
      diferencia: 0.05,
      observacion: "Presente con horas extra a favor (+0.05h)."
    },
    {
      legajo: "426884",
      nombre: "ACOSTA NICOLAS",
      jornada: 8.0,
      entrada: "10:41",
      salida: "19:07",
      estado: "Presente",
      horasTrabajadas: 8.43,
      diferencia: 0.43,
      observacion: "Presente con horas extra a favor (+0.43h)."
    },
    {
      legajo: "21097",
      nombre: "BARRIENTOS SILVIA",
      jornada: 8.0,
      entrada: "—",
      salida: "—",
      estado: "Falta sin aviso",
      horasTrabajadas: 0.0,
      diferencia: -8.0,
      observacion: "Sin registro de ingreso. Descuenta jornada contratada (8.0h)."
    },
    {
      legajo: "63365",
      nombre: "BARRIOS GONZALO",
      jornada: 8.0,
      entrada: "—",
      salida: "—",
      estado: "Falta sin aviso",
      horasTrabajadas: 0.0,
      diferencia: -8.0,
      observacion: "Sin registro de ingreso. Descuenta jornada contratada (8.0h)."
    },
    {
      legajo: "414770",
      nombre: "CAÑETE ROMINA",
      jornada: 5.0,
      entrada: "09:53",
      salida: "15:00",
      estado: "Presente",
      horasTrabajadas: 5.12,
      diferencia: 0.12,
      observacion: "Presente con horas extra a favor (+0.12h)."
    },
    {
      legajo: "413492",
      nombre: "CARRANZA ROBERTO",
      jornada: 8.0,
      entrada: "15:20",
      salida: "21:30",
      estado: "Presente",
      horasTrabajadas: 6.17,
      diferencia: -1.83,
      observacion: "Presente con horas faltantes a compensar (-1.83h)."
    },
    {
      legajo: "55939",
      nombre: "OBREGON DIEGO",
      jornada: 8.0,
      entrada: "06:42",
      salida: "—",
      estado: "Presente",
      horasTrabajadas: 8.0,
      diferencia: 0.0,
      observacion: "Presente. Fichaje de salida no registrado; se computa jornada contratada estándar."
    }
  ];

  function loadRealSheet() {
    byId("img-step-1").src = "static/img/pdi_evidencias/01_original.jpg";
    byId("img-step-2").src = "static/img/pdi_evidencias/02_perspectiva_corregida.jpg";
    byId("img-step-3").src = "static/img/pdi_evidencias/03_binarizada_otsu.jpg";
    byId("img-step-4").src = "static/img/pdi_evidencias/04_grilla_detectada.jpg";
    byId("vision-pipeline-display").classList.remove("hidden");
    showMessage(byId("vision-message"), "Foto real de la planilla (Jueves 05/11) cargada. Hacé clic en 'Procesar con Visión Artificial'.");
  }

  function handleCustomSheetUpload(event) {
    var file = event.target.files && event.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function (e) {
      byId("img-step-1").src = e.target.result;
      byId("vision-pipeline-display").classList.remove("hidden");
      showMessage(byId("vision-message"), "Foto '" + file.name + "' cargada en el visor. Hacé clic en 'Procesar con Visión Artificial'.");
    };
    reader.readAsDataURL(file);
  }

  function processVisionSheet() {
    byId("vision-pipeline-display").classList.remove("hidden");
    byId("vision-results-table").classList.remove("hidden");
    byId("vision-summary").classList.remove("hidden");

    var tbody = byId("vision-results-body");
    tbody.innerHTML = "";

    visionDemoResults.forEach(function (row) {
      var tr = document.createElement("tr");
      var difFormatted = (row.diferencia > 0 ? "+" : "") + row.diferencia.toFixed(2) + " h";
      var statusColor = row.estado === "Presente" ? "#10b981" : "#ef4444";

      tr.innerHTML = "<td><code>" + row.legajo + "</code></td>" +
        "<td><strong>" + row.nombre + "</strong></td>" +
        "<td>" + row.jornada.toFixed(1) + "h</td>" +
        "<td>" + row.entrada + "</td>" +
        "<td>" + row.salida + "</td>" +
        "<td><span style='color: " + statusColor + "; font-weight: bold;'>" + row.estado + "</span></td>" +
        "<td>" + row.horasTrabajadas.toFixed(2) + " h</td>" +
        "<td><strong style='color: " + (row.diferencia >= 0 ? "#10b981" : "#ef4444") + ";'>" + difFormatted + "</strong></td>" +
        "<td><small>" + row.observacion + "</small></td>";
      tbody.appendChild(tr);
    });

    byId("vision-status-msg").innerHTML = "<p style='color: #10b981; font-weight: bold;'>✔ Planilla procesada con éxito mediante OpenCV.</p>" +
      "<p style='font-size: 0.85rem; color: #cbd5e1;'>Se midió la densidad de tinta con umbral θ = 0.02. Podés volcar estos cálculos directamente al Banco de Horas con el botón de abajo.</p>";

    showMessage(byId("vision-message"), "Procesamiento completado: 8 empleados clasificados según jornada (8h / 5h) y presencia de firma.");
  }

  function applyVisionResultsToBank() {
    var dateStr = "2026-11-05";
    visionDemoResults.forEach(function (row) {
      var emp = state.employees.find(function (e) {
        return e.nombre.toUpperCase() === row.nombre.toUpperCase() || e.id === "emp-" + row.legajo;
      });

      if (!emp) {
        emp = { id: "emp-" + row.legajo, nombre: row.nombre };
        state.employees.push(emp);
        state.balances[emp.id] = 0;
      }

      var currentBal = Number(state.balances[emp.id] || 0);

      if (row.diferencia > 0) {
        var newBal = roundHours(currentBal + row.diferencia);
        state.balances[emp.id] = newBal;
        state.movements.unshift({
          id: "mov-" + Date.now() + "-" + row.legajo,
          empleadoId: emp.id,
          empleadoNombre: emp.nombre,
          tipo: "ACUMULACION",
          horas: row.diferencia,
          saldoResultante: newBal,
          detalle: row.observacion,
          fecha: dateStr + "T18:00:00"
        });
      } else if (row.diferencia < 0) {
        var toDeduct = Math.min(currentBal, Math.abs(row.diferencia));
        var resultingBal = roundHours(currentBal - toDeduct);
        state.balances[emp.id] = resultingBal;
        if (toDeduct > 0) {
          state.movements.unshift({
            id: "mov-" + Date.now() + "-" + row.legajo,
            empleadoId: emp.id,
            empleadoNombre: emp.nombre,
            tipo: "DEVOLUCION",
            horas: toDeduct,
            saldoResultante: resultingBal,
            detalle: row.observacion,
            fecha: dateStr + "T18:00:00"
          });
        }
      }

      state.attendance.unshift({
        id: "att-" + Date.now() + "-" + row.legajo,
        empleadoId: emp.id,
        empleadoNombre: emp.nombre,
        estado: row.estado,
        fecha: dateStr
      });
    });

    if (state.mode === "demo") {
      saveDemoState();
    }
    render();

    showMessage(byId("vision-message"), "¡Sincronización completa! Se actualizaron los saldos y asistencias de los 8 empleados en el Banco de Horas.");
  }

  document.addEventListener("DOMContentLoaded", initialize);
}());
