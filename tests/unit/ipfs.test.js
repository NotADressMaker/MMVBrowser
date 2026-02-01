const { ipfsToGateway } = require("../../src/server/ipfs");

describe("ipfsToGateway", () => {
  it("converts ipfs URIs", () => {
    const result = ipfsToGateway("https://ipfs.example", "ipfs://bafy123");
    expect(result).toBe("https://ipfs.example/ipfs/bafy123");
  });

  it("passes through https URIs", () => {
    const result = ipfsToGateway("https://ipfs.example", "https://example.com/data.json");
    expect(result).toBe("https://example.com/data.json");
  });
});
