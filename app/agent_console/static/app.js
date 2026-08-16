/**
 * 控制台前端：主页 Token 入 API 页；管理员成对签发。
 */
(function () {
  const $ = (id) => document.getElementById(id);
  const plain = { showG: "", showA: "" };

  function show(view) {
    ["viewHome", "viewApi", "viewAdmin"].forEach((id) => {
      $(id).classList.toggle("hidden", id !== view);
    });
  }

  function mask(s) {
    if (!s) return "";
    if (s.length <= 10) return "••••••••";
    return s.slice(0, 6) + "••••••••" + s.slice(-4);
  }

  function renderToken(elId) {
    const el = $(elId);
    const masked = el.getAttribute("data-masked") === "1";
    el.textContent = masked ? mask(plain[elId]) : plain[elId];
  }

  $("btnEnterApi").onclick = async () => {
    $("homeErr").classList.add("hidden");
    const token = $("tokenInput").value.trim();
    if (!token) {
      $("homeErr").textContent = "请填写 G 或 A Token";
      $("homeErr").classList.remove("hidden");
      return;
    }
    const res = await fetch("/console/api/tenant/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      $("homeErr").textContent = data.detail || "登录失败";
      $("homeErr").classList.remove("hidden");
      return;
    }
    await loadTenant();
  };

  async function loadTenant() {
    const res = await fetch("/console/api/tenant/me");
    if (!res.ok) {
      show("viewHome");
      return;
    }
    const data = await res.json();
    const p = data.pair;
    $("apiName").textContent = p.display_name || "";
    plain.showG = p.g_token;
    plain.showA = p.a_token;
    $("showG").setAttribute("data-masked", "1");
    $("showA").setAttribute("data-masked", "1");
    renderToken("showG");
    renderToken("showA");
    $("goGuide").textContent = data.guide || "";
    const epMap = {};
    (data.endpoints || []).forEach((e) => {
      epMap[e.tool_key] = e;
    });
    const list = $("toolList");
    list.innerHTML = "";
    (data.catalog || []).forEach((tool) => {
      const ep = epMap[tool.key] || {};
      const card = document.createElement("div");
      card.className = "tool-card";
      const params = (tool.params || [])
        .map(
          (x) =>
            `<li><code>${x.name}</code> ${x.required ? "<b>必填</b>" : "可选"} — ${x.desc}</li>`
        )
        .join("");
      const resp = (tool.response || [])
        .map(
          (x) =>
            `<li><code>${x.name}</code> ${x.required ? "<b>必填</b>" : "可选"} — ${x.desc}</li>`
        )
        .join("");
      card.innerHTML = `
        <h3>${tool.title} <small>(${tool.key})</small></h3>
        <div class="meta">${tool.method} · ${tool.description}</div>
        <label>完整 URL</label>
        <input data-url="${tool.key}" value="${ep.url || ""}" placeholder="https://example.com/..." />
        <label>上游 Bearer（可选）</label>
        <input data-auth="${tool.key}" value="${ep.upstream_auth || ""}" />
        <div class="params"><b>入参</b><ul>${params || "<li>无</li>"}</ul></div>
        <div class="params"><b>出参（经 Python 塑形后）</b><ul>${resp}</ul></div>
        <button type="button" class="btn btn-primary btn-sm" data-save="${tool.key}">保存</button>
        <span class="ok hidden" data-msg="${tool.key}"></span>
      `;
      list.appendChild(card);
    });
    list.querySelectorAll("[data-save]").forEach((btn) => {
      btn.onclick = async () => {
        const key = btn.getAttribute("data-save");
        const url = list.querySelector(`[data-url="${key}"]`).value.trim();
        const auth = list.querySelector(`[data-auth="${key}"]`).value.trim();
        const cat = (data.catalog || []).find((t) => t.key === key);
        const res2 = await fetch("/console/api/tenant/endpoints", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tool_key: key,
            url,
            method: (cat && cat.method) || "POST",
            upstream_auth: auth,
          }),
        });
        const msg = list.querySelector(`[data-msg="${key}"]`);
        if (res2.ok) {
          msg.textContent = "已保存";
          msg.classList.remove("hidden");
        } else {
          const err = await res2.json().catch(() => ({}));
          msg.textContent = err.detail || "失败";
          msg.classList.remove("hidden");
          msg.classList.remove("ok");
          msg.classList.add("err");
        }
      };
    });
    show("viewApi");
  }

  document.body.addEventListener("click", (ev) => {
    const t = ev.target;
    if (t.matches("[data-toggle]")) {
      const id = t.getAttribute("data-toggle");
      const el = $(id);
      const on = el.getAttribute("data-masked") === "1";
      el.setAttribute("data-masked", on ? "0" : "1");
      t.textContent = on ? "隐藏" : "显示";
      renderToken(id);
    }
    if (t.matches("[data-copy]")) {
      const id = t.getAttribute("data-copy");
      navigator.clipboard.writeText(plain[id] || "");
      t.textContent = "已复制";
      setTimeout(() => (t.textContent = "复制"), 1200);
    }
  });

  $("btnLogoutTenant").onclick = () => {
    document.cookie = "agent_tenant=; Max-Age=0; path=/";
    show("viewHome");
  };

  $("btnAdminEntry").onclick = () => {
    $("adminModal").classList.remove("hidden");
    $("adminErr").classList.add("hidden");
  };
  $("btnAdminCancel").onclick = () => $("adminModal").classList.add("hidden");
  $("btnAdminOk").onclick = async () => {
    const res = await fetch("/console/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: $("adminUser").value.trim(),
        password: $("adminPass").value,
      }),
    });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      $("adminErr").textContent = d.detail || "登录失败";
      $("adminErr").classList.remove("hidden");
      return;
    }
    $("adminModal").classList.add("hidden");
    await loadAdmin();
  };

  async function loadAdmin() {
    const res = await fetch("/console/api/admin/pairs");
    if (!res.ok) {
      show("viewHome");
      return;
    }
    const data = await res.json();
    const box = $("pairTable");
    let html =
      "<table><tr><th>ID</th><th>名称</th><th>G</th><th>A</th><th>G状态</th><th>操作</th></tr>";
    (data.pairs || []).forEach((p) => {
      html += `<tr>
        <td>${p.id}</td>
        <td>${p.display_name}</td>
        <td><code>${mask(p.g_token)}</code></td>
        <td><code>${mask(p.a_token)}</code></td>
        <td>${p.g_enabled ? "生效" : "失效"}</td>
        <td>
          <button class="btn btn-ghost btn-sm" data-en="${p.id}" data-v="${p.g_enabled ? 0 : 1}">
            ${p.g_enabled ? "设为失效" : "设为生效"}
          </button>
        </td>
      </tr>`;
    });
    html += "</table>";
    box.innerHTML = html;
    box.querySelectorAll("[data-en]").forEach((btn) => {
      btn.onclick = async () => {
        await fetch("/console/api/admin/g_enabled", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            pair_id: Number(btn.getAttribute("data-en")),
            enabled: btn.getAttribute("data-v") === "1",
          }),
        });
        loadAdmin();
      };
    });
    show("viewAdmin");
  }

  $("btnIssue").onclick = async () => {
    const res = await fetch("/console/api/admin/issue", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ display_name: $("issueName").value.trim() }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      alert(data.detail || "签发失败");
      return;
    }
    const p = data.pair;
    const text = `display_name: ${p.display_name}\nG: ${p.g_token}\nA: ${p.a_token}`;
    $("issueResult").textContent = text;
    $("issueResult").classList.remove("hidden");
    navigator.clipboard.writeText(text).catch(() => {});
    loadAdmin();
  };

  $("btnBackHome").onclick = () => show("viewHome");
  $("btnLogoutAdmin").onclick = () => {
    document.cookie = "agent_admin=; Max-Age=0; path=/";
    show("viewHome");
  };

  // 若已有租户 cookie 则尝试恢复
  fetch("/console/api/tenant/me").then((r) => {
    if (r.ok) loadTenant();
  });
})();
