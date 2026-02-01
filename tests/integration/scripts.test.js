process.env.API_BASE_URL = "https://mmv.test";
process.env.IPFS_GATEWAY = "https://ipfs.test";
process.env.GENAIL_RUNNER_MODE = "node";

const { http, HttpResponse } = require("msw");
const { setupServer } = require("msw/node");
const request = require("supertest");

const server = setupServer(
  http.get("https://mmv.test/records", () => {
    return HttpResponse.json({ items: [{ task_id: "task-1", score_bps: 9000 }] });
  })
);

const { app } = require("../../src/server/app");

describe("/api/scripts/run", () => {
  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  it("runs a script that lists records", async () => {
    const response = await request(app)
      .post("/api/scripts/run")
      .send({ script: "call mmv_list_records into records" });
    expect(response.status).toBe(200);
    expect(response.body.artifacts.records.items[0].task_id).toBe("task-1");
  });
});
