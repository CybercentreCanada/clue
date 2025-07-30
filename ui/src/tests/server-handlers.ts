import type { ActionResult } from 'lib/types/action';
import type { FetcherJsonResult } from 'lib/types/fetcher';
import type { Selector } from 'lib/types/lookup';
import cloneDeep from 'lodash-es/cloneDeep';
import set from 'lodash-es/set';
import { http, HttpResponse } from 'msw';
import actionExample from './models/action.example.json';
import classificationExample from './models/classification.example.json';
import enrichExample from './models/enrich.example.json';
import fetcherExample from './models/fetcher.example.json';

export const MOCK_RESPONSES = {
  '/api/v1/lookup/types': { example: ['ip'], potato: ['ip', 'sha256'] },
  '/api/v1/lookup/types_detection': {
    ip: '^[0-9\\.]+$',
    sha256: '[a-z]{4,64}'
  },
  '/api/v1/configs': {
    configuration: {
      auth: {
        oauth_providers: []
      },
      system: {
        version: '1.0.0',
        branch: 'develop',
        commit: 'abcd1234'
      },
      ui: {
        apps: []
      }
    },
    c12nDef: classificationExample
  },
  '/api/v1/actions': {
    'example.action': actionExample
  },
  '/api/v1/fetchers': {
    'example.fetcher': fetcherExample
  },
  '/api/v1/fetchers/example/fetcher': {
    outcome: 'success',
    link: 'http://example.com',
    format: 'json',
    data: {
      hello: 'world'
    }
  } as FetcherJsonResult,
  '/api/v1/actions/execute/example/action': {
    outcome: 'success',
    link: 'http://example.com',
    format: 'json',
    summary: 'great success',
    output: {
      hello: 'world'
    }
  } as ActionResult,
  '/api/v1/static/docs': {
    markdown: 'Hello World'
  },
  '/api/v1/static/docs/example': {
    markdown: 'Hello World'
  }
};

const handlers = [
  ...Object.entries(MOCK_RESPONSES).map(([path, data]) =>
    http.all(path, async () => HttpResponse.json({ api_response: data }))
  ),
  http.post('/api/v1/lookup/enrich', async ({ request }) => {
    const body = await request.json();

    if (Array.isArray(body) && body.length < 1) {
      return HttpResponse.json({
        api_response: {}
      });
    }

    return HttpResponse.json({
      api_response: {
        ip: Object.fromEntries(
          (body as Selector[]).map(entry => [entry.value, set(cloneDeep(enrichExample), 'example.value', entry.value)])
        )
      }
    });
  }),

  // AxiosClient test handlers
  http.get('/test/get', () =>
    HttpResponse.json({
      api_response: { method: 'GET', success: true },
      api_error_message: '',
      api_server_version: '1.0.0',
      api_status_code: 200
    })
  ),

  http.post('/test/post', async ({ request }) => {
    if (!request.body) {
      return HttpResponse.json(
        {
          api_response: { method: 'POST', body: null, success: true },
          api_error_message: '',
          api_server_version: '1.0.0',
          api_status_code: 200
        },
        { status: 201 }
      );
    }

    const body: any = await request.json();

    return HttpResponse.json(
      {
        api_response: { method: 'POST', body, success: true },
        api_error_message: '',
        api_server_version: '1.0.0',
        api_status_code: body?.status ?? 200
      },
      { status: body?.status ?? 201 }
    );
  }),

  http.put('/test/put', async ({ request }) => {
    const body: any = await request.json();
    return HttpResponse.json(
      {
        api_response: { method: 'PUT', body, success: true },
        api_error_message: '',
        api_server_version: '1.0.0',
        api_status_code: body?.status ?? 200
      },
      { status: body?.status ?? 200 }
    );
  }),

  http.patch('/test/patch', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      api_response: { method: 'PATCH', body, success: true },
      api_error_message: '',
      api_server_version: '1.0.0',
      api_status_code: 200
    });
  }),

  http.delete('/test/delete', () =>
    HttpResponse.json(
      {
        api_response: { method: 'DELETE', success: true },
        api_error_message: '',
        api_server_version: '1.0.0',
        api_status_code: 204
      },
      { status: 204 }
    )
  ),

  http.get('/test/error/400', () =>
    HttpResponse.json(
      {
        api_response: null,
        api_error_message: 'Bad Request',
        api_server_version: '1.0.0',
        api_status_code: 400
      },
      { status: 400 }
    )
  ),

  http.get('/test/error/500', () =>
    HttpResponse.json(
      {
        api_response: null,
        api_error_message: 'Internal Server Error',
        api_server_version: '1.0.0',
        api_status_code: 500
      },
      { status: 500 }
    )
  ),

  http.get('/test/error/502', () =>
    HttpResponse.json(
      {
        api_response: null,
        api_error_message: 'Bad Gateway',
        api_server_version: '1.0.0',
        api_status_code: 502
      },
      { status: 502 }
    )
  ),

  http.get('/test/error/429', () =>
    HttpResponse.json(
      {
        api_response: null,
        api_error_message: 'Too Many Requests',
        api_server_version: '1.0.0',
        api_status_code: 429
      },
      { status: 429 }
    )
  ),

  http.get('/test/with-etag', () =>
    HttpResponse.json(
      {
        api_response: { cached: true, timestamp: Date.now() },
        api_error_message: '',
        api_server_version: '1.0.0',
        api_status_code: 200
      },
      {
        headers: {
          ETag: 'test-etag-123'
        }
      }
    )
  ),

  http.get('/test/with-etag-no-cache', ({ request }) => {
    const ifMatch = request.headers.get('If-Match');
    if (ifMatch === 'test-etag-123') {
      return new HttpResponse(null, { status: 304 });
    }
    return HttpResponse.json(
      {
        api_response: { cached: true, timestamp: Date.now() },
        api_error_message: '',
        api_server_version: '1.0.0',
        api_status_code: 200
      },
      {
        headers: {
          ETag: 'test-etag-123'
        }
      }
    );
  }),

  http.get('/test/network-error', () => HttpResponse.error()),

  http.get('/test/with-params', ({ request }) => {
    const url = new URL(request.url);
    const params = Object.fromEntries(url.searchParams.entries());
    return HttpResponse.json({
      api_response: { params, success: true },
      api_error_message: '',
      api_server_version: '1.0.0',
      api_status_code: 200
    });
  }),

  http.get('/test/json-response', () =>
    HttpResponse.json({
      api_response: {
        user: { id: 1, name: 'test user' },
        metadata: { tags: ['tag1', 'tag2'], count: 42 },
        settings: null
      },
      api_error_message: '',
      api_server_version: '1.0.0',
      api_status_code: 200
    })
  )
];

export { handlers };
