const { shapeRecordList, shapeReceipt } = require("../../src/server/mmvTools");

describe("mmvTools shaping", () => {
  it("shapes record list", () => {
    const shaped = shapeRecordList({ items: [{ task_id: "task-1", score_bps: 8500, program_id: "prog" }] });
    expect(shaped).toEqual([
      { task_id: "task-1", score_bps: 8500, program_id: "prog" },
    ]);
  });

  it("shapes receipt", () => {
    const shaped = shapeReceipt({ id: "task-2", status: "verified", bundle_uri: "ipfs://hash" });
    expect(shaped).toEqual({
      task_id: "task-2",
      status: "verified",
      evidence_bundle_uri: "ipfs://hash",
    });
  });
});
