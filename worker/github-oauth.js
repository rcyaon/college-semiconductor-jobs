// Optional: one-click "Sign in with GitHub" for the website.
//
// GitHub's sign-in ends with a code that must be swapped for a token using the
// OAuth App's client secret. A static GitHub Pages site can't keep a secret, so
// this tiny Cloudflare Worker does the swap. It stores nothing.
//
// Setup is in the README under "Optional: GitHub sign-in". Needs these settings:
//   GITHUB_CLIENT_ID      (variable)
//   GITHUB_CLIENT_SECRET  (secret)
//   ALLOWED_ORIGIN        (variable), e.g. https://rcyaon.github.io

export default {
  async fetch(request, env) {
    const cors = {
      "Access-Control-Allow-Origin": env.ALLOWED_ORIGIN,
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };
    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    if (request.method !== "POST" || request.headers.get("Origin") !== env.ALLOWED_ORIGIN) {
      return new Response("Not allowed", { status: 403, headers: cors });
    }

    const { code } = await request.json().catch(() => ({}));
    if (!code) return Response.json({ error: "missing code" }, { status: 400, headers: cors });

    const res = await fetch("https://github.com/login/oauth/access_token", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ client_id: env.GITHUB_CLIENT_ID, client_secret: env.GITHUB_CLIENT_SECRET, code }),
    });
    const data = await res.json();
    if (!data.access_token) return Response.json({ error: data.error || "exchange failed" }, { status: 400, headers: cors });
    return Response.json({ access_token: data.access_token }, { headers: cors });
  },
};
