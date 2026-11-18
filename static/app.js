const $ = (id) => document.getElementById(id);
const video = $("video");
const photo = $("photo");
const overlay = $("overlay");
const ctx = overlay.getContext("2d");
const grabber = document.createElement("canvas");

const GREEN = "#16a34a";
const RED = "#dc2626";
// Kamera kadri serverga shu o'lchamgacha kichraytirib yuboriladi (tezlik uchun).
const RECOGNIZE_SIDE = 640;

let mode = "camera"; // "camera" — jonli kamera, "photo" — yuklangan rasm
let stream = null;
let loopId = 0; // yangi tsikl boshlanganda oshadi, eskisi o'zi to'xtaydi
let lastData = null;
let pending = []; // saqlanishini kutayotgan rasmlar: { blob, url }

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function setStatus(text, kind = "") {
  $("status").textContent = text;
  $("status").className = `status ${kind}`;
}

function describe(face) {
  const pct = Math.round(face.percent);
  if (face.known) return `${face.name} — ${pct}%`;
  if (!face.name) return "Noma'lum";
  return `Noma'lum (${face.name}? ${pct}%)`;
}

async function recognize(blob) {
  const form = new FormData();
  form.append("image", blob, "frame.jpg");
  const res = await fetch("/api/recognize", { method: "POST", body: form });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Server xatosi");
  return data;
}

// ---- Kamera ----

async function startCamera() {
  if (!stream) {
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
    } catch {
      showPlaceholder("Kamera ochilmadi. Brauzerga kamera ruxsatini bering yoki «Rasm bilan tekshirish» tugmasidan foydalaning.");
      setStatus("Kamera yo'q", "error");
      $("cameraBtn").hidden = false;
      return;
    }
    video.srcObject = stream;
  }
  await video.play();
  mode = "camera";
  lastData = null;
  video.hidden = false;
  photo.hidden = true;
  $("placeholder").hidden = true;
  $("cameraBtn").hidden = true;
  recognizeLoop(++loopId);
}

function showPlaceholder(text) {
  video.hidden = true;
  photo.hidden = true;
  $("placeholder").textContent = text;
  $("placeholder").hidden = false;
  lastData = null;
  draw();
}

function grabFrame(maxSide) {
  const scale = Math.min(1, maxSide / Math.max(video.videoWidth, video.videoHeight));
  grabber.width = Math.round(video.videoWidth * scale);
  grabber.height = Math.round(video.videoHeight * scale);
  grabber.getContext("2d").drawImage(video, 0, 0, grabber.width, grabber.height);
  return new Promise((resolve) => grabber.toBlob(resolve, "image/jpeg", 0.9));
}

async function recognizeLoop(id) {
  let frames = 0;
  let since = performance.now();
  while (id === loopId) {
    if (video.readyState < 2) {
      await sleep(100);
      continue;
    }
    try {
      const data = await recognize(await grabFrame(RECOGNIZE_SIDE));
      if (id !== loopId) break;
      show(data);
      frames += 1;
      const elapsed = performance.now() - since;
      if (elapsed > 1000) {
        $("fps").textContent = `${((frames * 1000) / elapsed).toFixed(1)} kadr/s`;
        frames = 0;
        since = performance.now();
      }
    } catch (err) {
      setStatus(err.message === "Failed to fetch" ? "Server bilan aloqa yo'q" : err.message, "error");
      await sleep(1000);
    }
  }
}

// ---- Natijani chizish ----

function show(data) {
  lastData = data;
  draw();
  renderResults(data.faces);
  if (data.people) setStatus(`Bazada ${data.people} ta odam`);
  else setStatus("Baza bo'sh — o'ngdan odam qo'shing", "warn");
}

function draw() {
  const media = mode === "camera" ? video : photo;
  const w = media.clientWidth;
  const h = media.clientHeight;
  const dpr = window.devicePixelRatio || 1;
  Object.assign(overlay.style, {
    left: `${media.offsetLeft}px`,
    top: `${media.offsetTop}px`,
    width: `${w}px`,
    height: `${h}px`,
  });
  overlay.width = Math.round(w * dpr);
  overlay.height = Math.round(h * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  if (!lastData || media.hidden) return;

  const scale = w / lastData.width;
  ctx.font = "600 14px system-ui, -apple-system, sans-serif";
  ctx.textBaseline = "middle";
  for (const face of lastData.faces) {
    let [x, y, bw, bh] = face.box.map((v) => v * scale);
    if (mode === "camera") x = w - x - bw; // video ko'zgudagidek aks ettirilgan
    const color = face.known ? GREEN : RED;
    ctx.lineWidth = 3;
    ctx.strokeStyle = color;
    ctx.strokeRect(x, y, bw, bh);

    const label = describe(face);
    const labelW = ctx.measureText(label).width + 14;
    const labelH = 26;
    const labelY = y >= labelH ? y - labelH : y + bh;
    ctx.fillStyle = color;
    ctx.fillRect(x - 1.5, labelY, labelW, labelH);
    ctx.fillStyle = "#fff";
    ctx.fillText(label, x + 6, labelY + labelH / 2);
  }
}

function renderResults(faces) {
  if (!faces.length) {
    const li = document.createElement("li");
    li.className = "muted";
    li.textContent = "Yuz topilmadi";
    $("results").replaceChildren(li);
    return;
  }
  $("results").replaceChildren(
    ...faces.map((face) => {
      const li = document.createElement("li");
      li.innerHTML = '<strong></strong><span class="pct"></span><div class="bar"><span></span></div>';
      const color = face.known ? GREEN : RED;
      li.querySelector("strong").textContent = face.known
        ? face.name
        : face.name ? `Noma'lum — eng yaqini: ${face.name}` : "Noma'lum";
      li.querySelector(".pct").textContent = `${Math.round(face.percent)}%`;
      li.querySelector(".pct").style.color = color;
      Object.assign(li.querySelector(".bar > span").style, { width: `${face.percent}%`, background: color });
      return li;
    }),
  );
}

window.addEventListener("resize", draw);

// ---- Rasm bilan tekshirish ----

$("checkFile").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  event.target.value = "";
  if (!file) return;
  loopId += 1; // kamera tsiklini to'xtatamiz
  mode = "photo";
  lastData = null;
  if (photo.src) URL.revokeObjectURL(photo.src);
  photo.src = URL.createObjectURL(file);
  try {
    await photo.decode();
  } catch {
    setStatus("Rasmni ochib bo'lmadi", "error");
    return;
  }
  photo.hidden = false;
  video.hidden = true;
  $("placeholder").hidden = true;
  $("cameraBtn").hidden = false;
  $("fps").textContent = "";
  setStatus("Tekshirilmoqda…");
  try {
    show(await recognize(file));
  } catch (err) {
    setStatus(err.message, "error");
  }
});

$("cameraBtn").addEventListener("click", startCamera);

// ---- Odam qo'shish ----

function addPending(blob) {
  pending.push({ blob, url: URL.createObjectURL(blob) });
  renderPending();
}

function renderPending() {
  $("shots").replaceChildren(
    ...pending.map((item, index) => {
      const shot = document.createElement("div");
      shot.className = "shot";
      const img = document.createElement("img");
      img.src = item.url;
      img.alt = "";
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "×";
      remove.title = "Olib tashlash";
      remove.addEventListener("click", () => {
        URL.revokeObjectURL(item.url);
        pending.splice(index, 1);
        renderPending();
      });
      shot.append(img, remove);
      return shot;
    }),
  );
  updateSaveButton();
}

function updateSaveButton() {
  $("saveBtn").disabled = !$("name").value.trim() || !pending.length;
  $("saveBtn").textContent = pending.length ? `Saqlash (${pending.length} ta rasm)` : "Saqlash";
}

$("name").addEventListener("input", updateSaveButton);

$("captureBtn").addEventListener("click", async () => {
  if (!stream || mode !== "camera" || video.readyState < 2) {
    setStatus("Suratga olish uchun kamera yoqilgan bo'lishi kerak", "warn");
    return;
  }
  $("stage").classList.add("flash");
  setTimeout(() => $("stage").classList.remove("flash"), 120);
  addPending(await grabFrame(Infinity));
});

$("files").addEventListener("change", (event) => {
  for (const file of event.target.files) addPending(file);
  event.target.value = "";
});

$("addForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = $("name").value.trim();
  if (!name || !pending.length) return;

  const form = new FormData();
  form.append("name", name);
  pending.forEach((item, i) => form.append("images", item.blob, item.blob.name || `kamera-${i + 1}.jpg`));
  $("saveBtn").disabled = true;
  $("saveBtn").textContent = "Saqlanmoqda…";
  try {
    const res = await fetch("/api/people", { method: "POST", body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Server xatosi");
    renderReport(name, data);
    pending.forEach((item) => URL.revokeObjectURL(item.url));
    pending = [];
    if (data.added) $("name").value = "";
    renderPending();
    loadPeople();
  } catch (err) {
    renderReport(name, { error: err.message });
    updateSaveButton();
  }
});

function renderReport(name, data) {
  const line = (text, cls) => {
    const li = document.createElement("li");
    li.className = cls;
    li.textContent = text;
    return li;
  };
  if (data.error) {
    $("report").replaceChildren(line(`✗ ${data.error}`, "bad"));
    return;
  }
  $("report").replaceChildren(
    line(`${name}: ${data.added} ta yuz qo'shildi`, data.added ? "ok" : "bad"),
    ...data.report.map((item) => {
      const notes = item.notes.length ? ` — ${item.notes.join("; ")}` : "";
      return line(`${item.ok ? "✓" : "✗"} ${item.file}${notes}`, item.ok ? "" : "bad");
    }),
  );
}

// ---- Bazadagi odamlar ----

async function loadPeople() {
  let people;
  try {
    people = await (await fetch("/api/people")).json();
  } catch {
    return;
  }
  $("count").textContent = people.length ? `(${people.length})` : "";
  if (!people.length) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "Hali hech kim qo'shilmagan";
    $("people").replaceChildren(li);
    return;
  }
  $("people").replaceChildren(
    ...people.map((person) => {
      const li = document.createElement("li");
      const info = document.createElement("div");
      info.className = "person";
      info.title = "Shu odamga yana rasm qo'shish";
      info.innerHTML = "<strong></strong><span class='muted'></span>";
      info.querySelector("strong").textContent = person.name;
      info.querySelector("span").textContent = `${person.faces} ta yuz`;
      info.addEventListener("click", () => {
        $("name").value = person.name;
        updateSaveButton();
        $("name").focus();
      });

      const remove = document.createElement("button");
      remove.className = "secondary small danger";
      remove.textContent = "O'chirish";
      remove.addEventListener("click", async () => {
        if (!confirm(`${person.name} bazadan o'chirilsinmi?`)) return;
        await fetch(`/api/people/${encodeURIComponent(person.name)}`, { method: "DELETE" });
        loadPeople();
      });
      li.append(info, remove);
      return li;
    }),
  );
}

loadPeople();
startCamera();
