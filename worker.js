export default {
  async fetch(request, env) {
    // 1. Handle CORS Preflight Requests (OPTIONS)
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization, x-goog-api-key',
          'Access-Control-Max-Age': '86400',
        }
      });
    }

    // 2. Parse the incoming request URL
    const url = new URL(request.url);
    
    // Default Gemini API Base URL
    const GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com';
    
    // Strip the worker domain, keep the path and query string.
    // Example incoming: https://my-worker.workers.dev/v1beta/models/gemini-3-pro-preview:streamGenerateContent
    // Target outgoing: https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-preview:streamGenerateContent
    const pathname = url.pathname === '/' ? '' : url.pathname;
    const targetUrl = new URL(pathname + url.search, GEMINI_BASE_URL);

    // 3. Prepare headers to forward to Gemini API
    const newHeaders = new Headers();
    
    // Pass along standard Request headers
    const contentType = request.headers.get('Content-Type');
    if (contentType) newHeaders.set('Content-Type', contentType);
    
    // Extract API Key
    const geminiKey = request.headers.get('x-goog-api-key');
    const authHeader = request.headers.get('Authorization');
    
    if (geminiKey) {
      newHeaders.set('x-goog-api-key', geminiKey);
    } else if (authHeader) {
      // Map 'Bearer <API_KEY>' to x-goog-api-key header if needed by Gemini
      const token = authHeader.replace(/^Bearer\s+/i, '').trim();
      newHeaders.set('x-goog-api-key', token);
    }

    // Optional: Pass streaming hint headers
    const accept = request.headers.get('Accept');
    if (accept) newHeaders.set('Accept', accept);

    // 4. Fire the Proxy Request
    try {
      const response = await fetch(targetUrl.toString(), {
        method: request.method,
        headers: newHeaders,
        body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : null,
        // Cloudflare Workers streaming support
        duplex: 'half'
      });

      // 5. Build our Response with injected CORS headers
      const respHeaders = new Headers(response.headers);
      // Never forward Content-Length: the body may be re-compressed or decompressed
      // in transit, and a stale length makes the browser cut the SSE stream short.
      respHeaders.delete('content-length');
      respHeaders.set('Access-Control-Allow-Origin', '*');
      respHeaders.set('Access-Control-Expose-Headers', '*');

      // Specifically handle SSE streaming flush configuration if returned text/event-stream
      const respContentType = response.headers.get('Content-Type');
      if (respContentType && respContentType.includes('text/event-stream')) {
        respHeaders.set('Cache-Control', 'no-cache');
        respHeaders.set('X-Accel-Buffering', 'no');
      }

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: respHeaders
      });
      
    } catch (error) {
      console.error(`Proxy Request Failed: ${error.message}`);
      return new Response(JSON.stringify({ error: error.message, target: targetUrl.toString() }), {
        status: 502,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      });
    }
  }
};
