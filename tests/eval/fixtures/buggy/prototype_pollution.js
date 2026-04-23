function merge(target, src) {
  for (const k in src) {
    if (typeof src[k] === "object") merge(target[k] = target[k] || {}, src[k]);
    else target[k] = src[k];
  }
  return target;
}
module.exports = (req, res) => res.json(merge({}, req.body));
