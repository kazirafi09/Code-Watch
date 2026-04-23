const { exec } = require("child_process");
module.exports = function lookup(domain, cb) {
  exec("whois " + domain, cb);
};
