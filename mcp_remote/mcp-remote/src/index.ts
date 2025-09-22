export default {
  async fetch(request: Request, env: any, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/get_time") {
      const now = new Date().toISOString();
      return new Response(JSON.stringify({ time: now }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response("MCP Remote Worker activo 🚀", { status: 200 });
  },
};
