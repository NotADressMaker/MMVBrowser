const {
  buildApiUrl,
  listRecords,
} = require("../../src/server/mmvClient");

describe("mmvClient", () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: [] }),
    });
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it("builds API URLs", () => {
    expect(buildApiUrl("https://mmv.example/", "/records")).toBe("https://mmv.example/records");
  });

  it("lists records with query params", async () => {
    await listRecords({ apiBaseUrl: "https://mmv.example", minScoreBps: 9000, limit: 10, offset: 5 });
    const url = global.fetch.mock.calls[0][0];
    expect(url).toContain("min_score_bps=9000");
    expect(url).toContain("limit=10");
    expect(url).toContain("offset=5");
  });
});
