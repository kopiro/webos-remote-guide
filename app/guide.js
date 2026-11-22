"use strict";

// Coordinates on LG's front-view photograph, measured on a 161 x 720 reference.
// Each target is at the edge of its cap so the arrow leaves the legend readable.
const layout = {
  "1": ["1", 21,72], "2": ["2",92,61], "3": ["3",141,72],
  "4": ["4",21,109], "5": ["5",92,98], "6": ["6",141,109],
  "7": ["7",21,146], "8": ["8",92,135], "9": ["9",141,146],
  guide:["Guide",20,183], "0":["0",69,195], "...":["•••",141,183],
  vol_up:["Vol +",21,220], vol_down:["Vol −",21,276], mute:["Mute",66,248],
  ch_up:["Ch +",141,219], ch_down:["Ch −",141,277], voice:["Mic",66,297],
  home:["Home",20,315], ok:["OK",98,380],
  red:["Red",18,474], green:["Green",51,483], yellow:["Yellow",107,484], blue:["Blue",143,474],
  netflix:["Netflix",15,504], prime:["Prime Video",147,504],
  disney:["Disney+",15,530], rakuten:["Rakuten TV",147,530],
  lg_channels:["LG Channels",15,557], alexa:["Alexa",147,557]
};
const sheet = document.querySelector("#sheet");
const keys = document.querySelector("#keys");
const lines = document.querySelector("#lines");
const statusBox = document.querySelector("#status");
const detail = document.querySelector("#detail");
const pager = document.querySelector("#pager");
const hotspots = document.querySelector("#hotspots");
const centers = {
  "1":[37,72], "2":[81,72], "3":[126,72], "4":[37,109], "5":[81,109], "6":[126,109],
  "7":[37,146], "8":[81,146], "9":[126,146], guide:[37,183], "0":[81,183], "...":[126,183],
  vol_up:[37,220],vol_down:[37,277],mute:[81,248],ch_up:[126,219],ch_down:[126,277],
  voice:[81,297],home:[37,315],ok:[81,380],red:[32,474],green:[64,477],
  yellow:[97,477],blue:[127,474],netflix:[45,504],prime:[113,504],disney:[45,530],
  rakuten:[113,530],lg_channels:[45,557],alexa:[113,557]
};
let control = null, pending = false;
const limit = 12;
let columns = [[], []], page = 0, activeKey = null, serialized = null, request = null;

function resize() {
  const scale = Math.min(innerWidth / 1920, innerHeight / 1080);
  sheet.style.transform = "translate(-50%, -50%) scale(" + scale + ")";
}
window.addEventListener("resize", resize);
resize();

function select(row, node) {
  activeKey = row.key;
  keys.querySelectorAll(".active").forEach(el => el.classList.remove("active"));
  lines.querySelectorAll(".active").forEach(el => el.classList.remove("active"));
  node.classList.add("active");
  const wire = document.getElementById("wire-" + row.key);
  if (wire) { wire.classList.add("active"); lines.appendChild(wire); }
  detail.textContent = row.detail || row.label;
}

async function activate(row) {
  if (pending || row.enabled === false) return;
  if (!control) { detail.textContent = "Shortcut control unavailable. Restart Magic Mapper."; return; }
  pending = true;
  detail.textContent = "Running · " + row.label;
  try {
    const response = await fetch("http://127.0.0.1:" + control.port + "/press", {
      method: "POST", headers: {"Authorization": "Bearer " + control.token, "Content-Type": "application/json"},
      body: JSON.stringify(row.key), credentials: "omit", redirect: "error"
    });
    if (!response.ok) throw new Error("Shortcut unavailable");
    detail.textContent = row.detail || row.label;
  } catch (_) {
    detail.textContent = "Could not run " + row.label + ".";
    refresh();
  } finally { pending = false; }
}

function addHotspot(row, button) {
  const center = centers[row.key];
  if (!center || !Array.isArray(center)) return;
  const hit = document.createElement("button");
  hit.className = "hotspot";
  hit.tabIndex = -1;
  hit.setAttribute("aria-label", button.textContent);
  hit.style.left = (864 + center[0] * 858 / 720) + "px";
  hit.style.top = (135 + center[1] * 858 / 720) + "px";
  hit.style.width = (["netflix","prime","disney","rakuten","lg_channels","alexa"].includes(row.key) ? 69 : 32) + "px";
  hit.onmouseenter = () => button.focus();
  hit.onclick = () => { button.focus(); activate(row); };
  hotspots.appendChild(hit);
}

function wireFor(row, side, y) {
  const target = layout[row.key];
  if (!Array.isArray(target)) return;
  const x = 864 + target[1] * 858 / 720;
  const ty = 135 + target[2] * 858 / 720;
  const start = side ? 1260 : 660;
  const knee = side ? 1205 : 715;
  const endKnee = side ? 1086 : 835;
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  // Center-column digits are approached through the gap between number rows.
  const upper = ["2","5","8"].includes(row.key);
  const entryY = upper ? ty - 7 : row.key === "0" ? ty + 9 : ty;
  const near = upper ? x + 12 : row.key === "0" ? x - 12 : x;
  path.setAttribute("d", "M " + start + " " + y + " H " + knee +
    " L " + endKnee + " " + entryY + " H " + near + " L " + x + " " + ty);
  path.id = "wire-" + row.key;
  lines.appendChild(path);
}

function render(focusFirst) {
  keys.textContent = "";
  hotspots.textContent = "";
  lines.textContent = "";
  const pages = Math.max(1, ...columns.map(column => Math.ceil(column.length / limit)));
  pager.hidden = pages < 2;
  pager.textContent = "Page " + (page + 1) + "/" + pages + "  ›";
  pager.onclick = () => nextPage(pages);
  const count = columns[0].length + columns[1].length;
  detail.textContent = count + (count === 1 ? " configured key" : " configured keys");
  statusBox.textContent = count ? "" : "No custom keys configured.";
  columns.forEach((column, side) => {
    const rows = column.slice(page * limit, (page + 1) * limit);
    rows.forEach((row, index) => {
      const y = 179 + index * Math.min(81, 770 / Math.max(1, rows.length - 1));
      wireFor(row, side, y);
      const button = document.createElement("button");
      button.className = "key " + (side ? "right" : "left");
      button.style.top = (y - 29) + "px";
      button.dataset.side = side;
      button.dataset.index = index;
      button.dataset.key = row.key;
      const cap = document.createElement("span");
      cap.className = "cap";
      cap.textContent = Array.isArray(layout[row.key]) ? layout[row.key][0] : row.key;
      const action = document.createElement("span");
      action.className = "action";
      action.textContent = row.label;
      button.append(cap, action);
      button.title = row.detail;
      button.onfocus = () => select(row, button);
      button.onmouseenter = () => button.focus();
      button.setAttribute("aria-disabled", String(row.enabled === false));
      button.onclick = () => { button.focus(); activate(row); };
      addHotspot(row, button);
      keys.appendChild(button);
    });
  });
  const chosen = Array.from(keys.children).find(el => el.dataset.key === activeKey);
  if (chosen || focusFirst || document.activeElement === document.body) (chosen || keys.firstElementChild)?.focus();
}
function nextPage(pages) { page = (page + 1) % pages; activeKey = null; render(true); }

window.receiveBindings = function(rows, device, channel) {
  control = channel || null;
  document.querySelector("#device").textContent = device ? device + "  /" : "";
  const value = JSON.stringify(rows);
  if (value === serialized) return;
  serialized = value;
  columns = [[], []];
  const known = rows.filter(row => Object.hasOwnProperty.call(layout, row.key));
  known.sort((a,b) => layout[a.key][2] - layout[b.key][2]);
  known.forEach(row => columns[layout[row.key][1] >= 81 ? 1 : 0].push(row));
  rows.filter(row => !known.includes(row)).forEach(row => {
    columns[columns[0].length <= columns[1].length ? 0 : 1].push(row);
  });
  page = 0;
  render(false);
};

function refresh() {
  if (document.hidden || request) return;
  const script = document.createElement("script");
  request = script;
  function finish() { script.remove(); request = null; }
  script.onerror = () => {
    serialized = null;
    keys.textContent = ""; lines.textContent = ""; hotspots.textContent = ""; detail.textContent = ""; pager.hidden = true; control = null;
    statusBox.textContent = "Key mappings unavailable. Waiting for Magic Mapper…";
    finish();
  };
  script.onload = finish;
  script.src = "bindings.js?t=" + Date.now();
  document.head.appendChild(script);
}
document.addEventListener("visibilitychange", refresh);
window.addEventListener("webOSRelaunch", refresh);
setInterval(refresh, 15000);
refresh();

document.addEventListener("keydown", event => {
  const code = event.keyCode;
  if (code === 13 && event.repeat) { event.preventDefault(); return; }
  if (![37,38,39,40].includes(code)) return;
  event.preventDefault();
  const current = document.activeElement;
  if (!current || !current.classList.contains("key")) { keys.firstElementChild?.focus(); return; }
  let side = Number(current.dataset.side), index = Number(current.dataset.index);
  if (code === 37 || code === 39) side = code === 39 ? 1 : 0;
  if (code === 38) index--;
  if (code === 40) index++;
  const siblings = keys.querySelectorAll('[data-side="' + side + '"]');
  if (!pager.hidden && ((code === 40 && index >= siblings.length) || (code === 38 && index < 0))) {
    const pages = Math.max(...columns.map(column => Math.ceil(column.length / limit)));
    page = (page + (code === 40 ? 1 : pages - 1)) % pages;
    activeKey = null; render(true); return;
  }
  if (siblings.length) siblings[Math.max(0, Math.min(siblings.length - 1, index))].focus();
});
