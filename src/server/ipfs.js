function ipfsToGateway(ipfsGateway, uri) {
  if (!uri) {
    return "";
  }
  if (uri.startsWith("ipfs://")) {
    return `${ipfsGateway.replace(/\/$/, "")}/ipfs/${uri.slice("ipfs://".length)}`;
  }
  return uri;
}

module.exports = { ipfsToGateway };
