let currentSessionId = null;

const uploadBtn = document.getElementById("uploadBtn");
const processBtn = document.getElementById("processBtn");

uploadBtn.addEventListener("click", async () => {
  const fileInput = document.getElementById("fileInput");
  const status = document.getElementById("uploadStatus");

  if (!fileInput.files.length) {
    status.textContent = "Please choose a CSV file first.";
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  status.textContent = "Uploading and scanning...";

  const res = await fetch("/upload", { method: "POST", body: formData });
  const data = await res.json();

  if (data.error) {
    status.textContent = "Error: " + data.error;
    return;
  }

  currentSessionId = data.session_id;
  status.textContent = `Loaded ${data.filename} (${data.num_records} records).`;
  document.getElementById("riskBefore").textContent = data.risk_before;
  renderColumnsTable(data.columns);
  document.getElementById("review-section").classList.remove("hidden");
});

function renderColumnsTable(columns) {
  const tbody = document.querySelector("#columnsTable tbody");
  tbody.innerHTML = "";

  columns.forEach(col => {
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${col.column}</td>
      <td>${col.label}</td>
      <td>${col.confidence}%</td>
      <td>${col.sample_values.join(", ")}</td>
      <td>
        <select data-column="${col.column}">
          <option value="skip" ${!col.detected ? "selected" : ""}>Skip</option>
          <option value="mask" ${col.detected ? "selected" : ""}>Mask</option>
          <option value="hash">Hash</option>
          <option value="encrypt">Encrypt</option>
          <option value="tokenize">Tokenize</option>
        </select>
      </td>
    `;
    tbody.appendChild(row);
  });
}

processBtn.addEventListener("click", async () => {
  const selects = document.querySelectorAll("#columnsTable select");
  const columnMethods = {};
  selects.forEach(sel => {
    columnMethods[sel.dataset.column] = sel.value;
  });

  const res = await fetch("/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: currentSessionId, column_methods: columnMethods })
  });

  const data = await res.json();
  if (data.error) {
    alert("Error: " + data.error);
    return;
  }

  document.getElementById("riskBeforeResult").textContent = data.risk_before;
  document.getElementById("riskAfterResult").textContent = data.risk_after;
  document.getElementById("csvLink").href = "/download/" + data.csv_download;
  document.getElementById("reportLink").href = "/download/" + data.report_download;

  if (data.encryption_key) {
    document.getElementById("encKey").textContent = data.encryption_key;
    document.getElementById("keyNotice").classList.remove("hidden");
  }

  document.getElementById("result-section").classList.remove("hidden");
});
