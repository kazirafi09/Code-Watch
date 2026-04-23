const { execFile } = require("child_process");
module.exports = function lookup(domain, cb) {
  execFile("whois", [domain], cb);
};
