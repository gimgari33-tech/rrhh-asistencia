(function () {
  "use strict";

  var STORAGE_KEY = "rrhh-asistencia-demo-v1";
  var state = {
    mode: "demo",
    db: null,
    auth: null,
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
    byId("mode-badge").textContent = state.mode === "demo" ? "DEMO LOCAL" : "FIREBASE";
    byId("mode-badge").classList.toggle("demo-badge", state.mode === "demo");
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
      initializeFirebaseMode();
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

  function initializeFirebaseMode() {
    state.mode = "firebase";
    try {
      state.auth = window.firebase.auth();
      state.db = window.firebase.firestore();
      byId("login-form").classList.remove("hidden");
      byId("login-error").textContent = "";
      state.auth.onAuthStateChanged(function (user) {
        if (!user) {
          setScreen(false);
          return;
        }
        loadFirebaseState().then(function () {
          showApplication(user.email || "Usuario autenticado");
        }).catch(function (error) {
          setScreen(false);
          showMessage(byId("login-error"), "No se pudieron cargar los datos: " + error.message, true);
        });
      });
    } catch (error) {
      state.mode = "demo";
      byId("login-form").classList.add("hidden");
      byId("login-error").textContent = "Firebase no está configurado. Podés entrar a la demo sin datos reales.";
    }
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
    if (state.mode === "firebase" && state.auth) {
      state.auth.signOut();
    } else {
      setScreen(false);
    }
  }

  function enterDemo() {
    state.mode = "demo";
    state.db = null;
    state.auth = null;
    var data = loadDemoState();
    state.employees = data.employees;
    state.balances = data.balances;
    state.movements = data.movements;
    state.attendance = data.attendance || [];
    state.filteredEmployeeId = null;
    showApplication("Demo pública");
  }

  function loadFirebaseState() {
    return state.db.collection("empleados").orderBy("nombre").get().then(function (snapshot) {
      state.employees = snapshot.docs.map(function (document) {
        return Object.assign({ id: document.id }, document.data());
      });
      return Promise.all(state.employees.map(function (employee) {
        return state.db.collection("bancos_horas").doc(employee.id).get().then(function (bank) {
          state.balances[employee.id] = bank.exists ? Number(bank.data().saldoHoras || 0) : 0;
        });
      }));
    }).then(function () {
      return state.db.collection("movimientos_banco_horas").orderBy("fecha", "desc").limit(100).get();
    }).then(function (snapshot) {
      state.movements = snapshot.docs.map(function (document) {
        var movement = Object.assign({ id: document.id }, document.data());
        movement.fecha = movement.fecha && movement.fecha.toDate ? movement.fecha.toDate().toISOString() : new Date().toISOString();
        return movement;
      });
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

    state.db.collection("empleados").add({
      nombre: name,
      creadoEn: window.firebase.firestore.FieldValue.serverTimestamp()
    }).then(function (document) {
      return state.db.collection("bancos_horas").doc(document.id).set({
        empleadoId: document.id,
        saldoHoras: 0,
        actualizadoEn: window.firebase.firestore.FieldValue.serverTimestamp()
      });
    }).then(function () {
      nameInput.value = "";
      return loadFirebaseState();
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

    var bankRef = state.db.collection("bancos_horas").doc(employeeId);
    var movementRef = state.db.collection("movimientos_banco_horas").doc();
    state.db.runTransaction(function (transaction) {
      return transaction.get(bankRef).then(function (bankSnapshot) {
        var current = bankSnapshot.exists ? Number(bankSnapshot.data().saldoHoras || 0) : 0;
        var next = kind === "ACUMULACION" ? current + hours : current - hours;
        if (next < 0) {
          throw new Error("La devolución supera las horas disponibles.");
        }
        next = roundHours(next);
        transaction.set(bankRef, {
          empleadoId: employeeId,
          saldoHoras: next,
          actualizadoEn: window.firebase.firestore.FieldValue.serverTimestamp()
        }, { merge: true });
        transaction.set(movementRef, {
          empleadoId: employeeId,
          empleadoNombre: employee.nombre,
          tipo: kind,
          horas: hours,
          saldoResultante: next,
          detalle: detail,
          fecha: window.firebase.firestore.FieldValue.serverTimestamp()
        });
      });
    }).then(function () {
      byId("movement-hours").value = "";
      byId("movement-note").value = "";
      return loadFirebaseState();
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

    entry.creadoEn = window.firebase.firestore.FieldValue.serverTimestamp();
    state.db.collection("asistencia").add(entry).then(function () {
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
