function shapeRecordList(payload) {
  const items = Array.isArray(payload?.items) ? payload.items : [];
  return items.map((item) => ({
    task_id: item.task_id || item.id || null,
    score_bps: item.score_bps ?? item.score ?? null,
    program_id: item.program_id || null,
  }));
}

function shapeReceipt(payload) {
  return {
    task_id: payload?.task_id || payload?.id || null,
    status: payload?.status || null,
    evidence_bundle_uri: payload?.evidence_bundle_uri || payload?.bundle_uri || null,
  };
}

module.exports = { shapeRecordList, shapeReceipt };
