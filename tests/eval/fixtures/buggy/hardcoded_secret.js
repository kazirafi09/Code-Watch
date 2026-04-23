const AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY";
export function sign(req) { return hmac(req, AWS_SECRET_ACCESS_KEY); }
