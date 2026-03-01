// Pinewood Derby — Registration Email Edge Function
// Deploy: supabase functions deploy send-registration-email
//
// Set this secret in Supabase Dashboard → Edge Functions → Secrets:
//   SMTP_PASSWORD = Fynnfynn2012

import nodemailer from "npm:nodemailer@6";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });

  try {
    const { to, kid_name, car_number, device_token, reg_url } =
      await req.json() as {
        to: string;
        kid_name: string;
        car_number: number;
        device_token: string;
        reg_url: string;
      };

    const smtpPass = Deno.env.get("SMTP_PASSWORD");
    if (!smtpPass) throw new Error("SMTP_PASSWORD secret not set in Supabase dashboard");

    const transporter = nodemailer.createTransport({
      host: "smtp.zoho.eu",
      port: 587,
      secure: false, // STARTTLS
      auth: { user: "fynn@fynn.qzz.io", pass: smtpPass },
    });

    // Derive 4-letter check-in code (same algorithm as the frontend)
    let hash = 0;
    for (let i = 0; i < device_token.length; i++) {
      hash = ((hash << 5) - hash) + device_token.charCodeAt(i);
      hash |= 0;
    }
    hash = Math.abs(hash);
    const letters = "ABCDEFGHJKLMNPQRSTUVWXYZ";
    let shortCode = "";
    for (let i = 0; i < 4; i++) {
      shortCode += letters[hash % letters.length];
      hash = Math.floor(hash / letters.length);
    }

    // QR code image (encodes device_token — same as the press-QR button on the page)
    const qrUrl =
      `https://api.qrserver.com/v1/create-qr-code/?size=260x260&data=${encodeURIComponent(device_token)}&bgcolor=ffffff&color=1a1e2e&margin=12`;

    await transporter.sendMail({
      from: '"PWD 🏎️" <pwd@fynn.qzz.io>',
      to,
      subject: `${kid_name} is registered — Car #${car_number} 🏁`,
      html: `<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8" /><meta name="viewport" content="width=device-width,initial-scale=1" /></head>
<body style="margin:0;padding:0;background:#f0f2f8;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f0f2f8;padding:32px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" border="0" style="max-width:520px;width:100%;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10);">

        <!-- Header -->
        <tr>
          <td style="background:#1a1e2e;padding:28px 32px;text-align:center;">
            <div style="font-size:2rem;">🏎️</div>
            <h1 style="margin:8px 0 4px;color:#f59e0b;font-size:1.5rem;font-weight:900;letter-spacing:1px;">PINEWOOD DERBY</h1>
            <p style="color:#6b738f;margin:0;font-size:0.85rem;letter-spacing:2px;text-transform:uppercase;">Registration Confirmed</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px;">
            <h2 style="margin:0 0 6px;color:#1a1e2e;font-size:1.3rem;">You're in! 🎉</h2>
            <p style="margin:0 0 24px;color:#555;line-height:1.6;"><strong>${kid_name}</strong>'s car has been successfully registered for race day.</p>

            <!-- Car number badge -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:24px;">
              <tr>
                <td style="background:#f8f9fa;border-radius:12px;padding:20px;text-align:center;">
                  <div style="font-size:0.7rem;font-weight:700;letter-spacing:4px;text-transform:uppercase;color:#888;margin-bottom:4px;">Car Number</div>
                  <div style="font-size:3.5rem;font-weight:900;color:#1a1e2e;line-height:1;">#${car_number}</div>
                  <div style="font-size:0.85rem;color:#1a1e2e;font-weight:700;margin-top:10px;letter-spacing:8px;">${shortCode}</div>
                  <div style="font-size:0.7rem;color:#888;margin-top:2px;">Check-in code</div>
                </td>
              </tr>
            </table>

            <!-- QR code -->
            <p style="margin:0 0 12px;color:#555;font-size:0.9rem;line-height:1.5;">Show this QR code at inspection to check in — it covers all cars registered from your device.</p>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:24px;">
              <tr>
                <td align="center">
                  <img src="${qrUrl}" width="200" height="200" alt="Check-in QR Code"
                       style="border-radius:10px;border:1px solid #e5e7eb;display:block;" />
                </td>
              </tr>
            </table>

            <!-- CTA button -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:24px;">
              <tr>
                <td align="center">
                  <a href="${reg_url}" style="display:inline-block;background:#f59e0b;color:#1a1e2e;text-decoration:none;padding:14px 32px;border-radius:10px;font-weight:700;font-size:0.95rem;">
                    📱 Open Registration Page
                  </a>
                </td>
              </tr>
            </table>

            <p style="margin:0;color:#aaa;font-size:0.78rem;text-align:center;line-height:1.6;">
              You can view your car's status and race schedule on the registration page during the event.<br>
              This email was sent by the Pinewood Derby race management system.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>`,
    });

    return new Response(JSON.stringify({ ok: true }), {
      headers: { ...CORS, "Content-Type": "application/json" },
    });
  } catch (err) {
    console.error("Email send error:", err);
    return new Response(JSON.stringify({ error: String(err) }), {
      status: 500,
      headers: { ...CORS, "Content-Type": "application/json" },
    });
  }
});
