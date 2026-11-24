/**
 * The website's stylesheet. Web pages are real DOM + CSS (`*.web.tsx`); the
 * React Native screens keep their own StyleSheets. Every colour here is a
 * value from `theme/tokens.ts` — exposed as CSS variables, not re-picked.
 */
import { colors as c } from '../theme/tokens';

const CSS = `
:root{
  --bg:${c.background};--paper:${c.surface};--sunk:${c.surfaceContainerLow};--sunk2:${c.surfaceContainer};
  --ink:${c.onSurface};--ink2:${c.onSurfaceVariant};--ink3:#7a6258;
  --line:${c.borderCard};--line2:${c.borderField};
  --brand:${c.primary};--brand2:${c.primaryContainer};--onbrand:${c.onPrimary};
  --good:${c.tertiary};--bad:${c.critical};--soil:#24120b;
  --font:'Plus Jakarta Sans','Mukta','Noto Sans Devanagari',system-ui,sans-serif;
  --wrap:1240px;--pad:clamp(16px,3.2vw,40px);--ease:cubic-bezier(.2,.7,.2,1);
}
.km,.km *{box-sizing:border-box}
.km{font-family:var(--font);color:var(--ink);font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums lining-nums}
:where(.km) :where(h1,h2,h3,p,dl,dd,figure,ul){margin:0;padding:0}
:where(.km) ul{list-style:none}
.km :where(button,select,input,textarea){font-family:inherit;font-size:inherit;line-height:inherit;font-weight:inherit;color:inherit}
:where(.km) :where(button){cursor:pointer;background:none;border:0;padding:0;text-align:inherit}
.km :focus-visible{outline:3px solid var(--brand2);outline-offset:3px;border-radius:6px}
:where(.km) :where(img){display:block}
.km-page{flex:1;min-height:0;height:100%;overflow-y:auto;overflow-x:hidden;background:var(--bg);scroll-behavior:smooth}
.km-wrap{max-width:calc(var(--wrap) + 2*var(--pad));margin:0 auto;padding-inline:var(--pad);width:100%}
.km-sec{padding-block:clamp(40px,5.5vw,76px)}
.km-h2{font-size:clamp(24px,2.6vw,34px);line-height:1.2;font-weight:700;letter-spacing:-.018em;text-wrap:balance}
.km-lede{color:var(--ink2);max-width:62ch;margin-top:8px!important}
.km-head{display:flex;align-items:end;justify-content:space-between;gap:24px;margin-bottom:28px;flex-wrap:wrap}
.km-btn{display:inline-flex;align-items:center;justify-content:center;gap:10px;min-height:50px;padding:0 24px!important;border-radius:12px;font-weight:700;background:var(--brand2)!important;color:var(--onbrand)!important;transition:background .18s,transform .18s}
.km-btn:hover{background:var(--brand)!important}.km-btn:active{transform:translateY(1px)}
.km-btn[disabled]{opacity:.5;cursor:default}
.km-btn.ghost{background:transparent!important;color:var(--brand)!important;box-shadow:inset 0 0 0 1.5px var(--brand2)}
.km-btn.ghost:hover{background:#fff4ee!important}
.km-link{font-weight:700;color:var(--brand)!important;text-decoration:underline;text-decoration-thickness:1.5px;text-underline-offset:5px;text-decoration-color:color-mix(in srgb,var(--brand2) 40%,transparent)}
.km-link:hover{text-decoration-color:var(--brand2)}
.km-seg{display:inline-flex;background:var(--sunk2);border-radius:10px;padding:4px}
.km-seg button{min-height:38px;padding:0 16px;border-radius:7px;font-weight:600;font-size:15px;color:var(--ink2)}
.km-seg button[aria-pressed=true]{background:var(--paper);color:var(--ink);box-shadow:0 1px 3px rgba(89,65,58,.16)}
.km-good{color:var(--good)}.km-bad{color:var(--bad)}.km-mut{color:var(--ink2)}
.km-note{font-size:14px;color:var(--ink2)}

/* nav */
.km-nav{position:relative;z-index:60;background:var(--bg);border-bottom:1px solid var(--line)}
.km-nav .km-wrap{height:72px;display:flex;align-items:center;gap:clamp(16px,2.4vw,36px)}
.km-brand{display:flex!important;align-items:center;gap:11px;font-weight:800;font-size:20px;letter-spacing:-.02em;color:var(--brand)!important;white-space:nowrap}
.km-tabs{display:flex;gap:4px;margin-right:auto;height:100%}
.km-tabs button{position:relative;height:100%;padding:0 14px;font-weight:600;color:var(--ink2);white-space:nowrap}
.km-tabs button:hover{color:var(--ink)}
.km-tabs button[aria-current=page]{color:var(--brand)}
.km-tabs button[aria-current=page]::after{content:'';position:absolute;left:14px;right:14px;bottom:-1px;height:3px;border-radius:3px 3px 0 0;background:var(--brand2)}
.km-tabs svg{display:none}
.km-lang{display:flex;gap:2px}
.km-lang button{min-height:38px;padding:0 10px;border-radius:8px;font-size:15px;font-weight:600;color:var(--ink2)}
.km-lang button[aria-pressed=true]{color:var(--onbrand);background:var(--brand)}
.km-me{position:relative}
.km-me>button{display:flex;align-items:center;gap:10px;font-weight:600;white-space:nowrap}
.km-ava{width:40px;height:40px;border-radius:50%;background:var(--brand2);color:#fff;display:grid;place-items:center;font-weight:700}
.km-menu{position:absolute;right:0;top:52px;min-width:232px;background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:8px;box-shadow:0 18px 44px -12px rgba(36,18,11,.28)}
.km-menu button{display:flex;width:100%;gap:12px;align-items:center;min-height:46px;padding:0 12px;border-radius:9px;font-weight:600}
.km-menu button:hover{background:var(--sunk)}

/* hero */
.km-hero{position:relative;isolation:isolate;color:#fff;background:var(--soil);overflow:hidden}
.km-hero-img{position:absolute;inset:0;z-index:-2;width:100%;height:100%;object-fit:cover;object-position:72% 50%;animation:kmfade .7s var(--ease) both}
.km-hero::before{content:'';position:absolute;inset:0;z-index:-1;background:linear-gradient(90deg,rgba(26,12,7,.88) 0%,rgba(26,12,7,.68) 34%,rgba(26,12,7,.1) 64%,rgba(26,12,7,0) 100%),linear-gradient(0deg,rgba(26,12,7,.62) 0%,rgba(26,12,7,0) 40%)}
.km-hero .km-wrap{display:flex;flex-direction:column;justify-content:flex-end;min-height:clamp(480px,64vh,640px);padding-block:44px 112px}
.km-hero h1{font-weight:800;font-size:clamp(52px,7.2vw,100px);line-height:1;letter-spacing:-.035em}
.km-hero h1[lang=mr],.km-hero h1[lang=hi]{letter-spacing:-.01em;line-height:1.12}
.km-hi{font-size:17px;font-weight:500;color:#f4e3d8;margin-bottom:auto!important}
.km-where{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-top:14px;font-size:18px;color:#f4e3d8}
.km-pick{position:relative;display:inline-flex;align-items:center}
.km-pick select{appearance:none;-webkit-appearance:none;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.3);color:#fff;font-weight:600;font-size:16px;border-radius:10px;min-height:46px;padding:0 40px 0 16px;cursor:pointer;backdrop-filter:blur(6px);max-width:min(320px,78vw);text-overflow:ellipsis}
.km-pick select:hover{background:rgba(255,255,255,.2)}
.km-pick select option{color:var(--ink);background:#fff}
.km-pick::after{content:'';position:absolute;right:17px;width:8px;height:8px;border:solid currentColor;border-width:0 2px 2px 0;transform:translateY(-3px) rotate(45deg);pointer-events:none}
.km-pick.light select{background:var(--paper);color:var(--ink);border-color:var(--line2);backdrop-filter:none}
.km-rate{display:flex;flex-wrap:wrap;align-items:end;gap:14px 44px;margin-top:34px}
.km-price{font-weight:800;font-size:clamp(44px,5.2vw,72px);line-height:1;letter-spacing:-.03em}
.km-price small{font-size:18px;font-weight:500;letter-spacing:0;color:#f4e3d8;margin-left:8px}
.km-chg{display:inline-flex;align-items:center;gap:7px;font-weight:700;font-size:18px}
.km-chg.up{color:#97f5cc}.km-chg.dn{color:#ffb59d}
.km-band{width:min(440px,100%);margin-top:6px}
.km-band-rule{position:relative;height:4px;border-radius:4px;background:rgba(255,255,255,.28)}
.km-band-rule i{position:absolute;top:50%;width:14px;height:14px;border-radius:50%;background:#fff;transform:translate(-50%,-50%);box-shadow:0 0 0 5px rgba(255,255,255,.22)}
.km-band dl{display:flex;justify-content:space-between;margin-top:12px!important;font-size:14px;color:#f4e3d8}
.km-band dd{color:#fff;font-weight:700;font-size:16px}
.km-src{margin-top:16px!important;font-size:14px;color:#ead4c6}

/* crop strip */
.km-strip{margin-top:24px}
.km-herowrap{padding-top:24px}
.km-herowrap .km-hero,.km-herowrap .km-banner{border-radius:22px}
.km-herowrap .km-banner .km-wrap{padding-inline:clamp(22px,3.4vw,48px)}
.km-herowrap .km-hero .km-wrap{padding-inline:clamp(22px,3.4vw,48px);padding-block:32px 36px;min-height:clamp(460px,58vh,560px)}
.km-strip ul{display:flex;gap:12px;overflow-x:auto;padding:8px 8px 14px;margin:0 -8px;scroll-padding:8px;scroll-snap-type:x proximity;scrollbar-width:thin}
.km-strip li{scroll-snap-align:start;flex:0 0 auto}
.km-tile{position:relative;display:block!important;width:128px;height:148px;border-radius:14px;overflow:hidden;background:var(--sunk2);box-shadow:0 8px 22px -10px rgba(36,18,11,.5)}
.km-tile img{width:100%;height:100%;object-fit:cover;transition:transform .5s var(--ease)}
.km-tile:hover img{transform:scale(1.06)}
.km-tile span{position:absolute;inset:auto 0 0;padding:34px 12px 10px;color:#fff;font-weight:700;font-size:16px;line-height:1.2;background:linear-gradient(0deg,rgba(26,12,7,.86),rgba(26,12,7,0))}
.km-tile[aria-pressed=true]{box-shadow:0 0 0 3px var(--bg),0 0 0 6px var(--brand2)}

/* advice */
.km-advice{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:clamp(28px,4vw,64px);align-items:start}
.km-advice.even{grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);gap:24px;align-items:stretch}
.km-verdict{font-size:clamp(34px,4vw,54px);font-weight:800;line-height:1.1;letter-spacing:-.025em;text-wrap:balance}
.km-verdict.hold{color:var(--brand)}.km-verdict.sell{color:var(--good)}.km-verdict.none{color:var(--ink2)}
.km-pair{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:24px!important}
.km-pair>div{padding:16px 18px;background:var(--sunk);border-radius:14px}
.km-pair dt{font-size:15px;color:var(--ink2)}
.km-pair dd{font-size:clamp(28px,2.9vw,38px);font-weight:800;letter-spacing:-.02em;line-height:1.25}
.km-costs{margin-top:20px!important}
.km-costs div{display:flex;justify-content:space-between;padding:7px 0;font-size:15px}
.km-costs dt{color:var(--ink2)}.km-costs dd{font-weight:600}
.km-costs .tot{border-top:1px solid var(--line2);margin-top:6px;padding-top:11px;font-weight:700}
.km-costs .tot dt{color:var(--ink)}
.km-row{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin-top:24px}
.km-sheet{background:var(--paper);border:1px solid var(--line);border-radius:20px;padding:clamp(18px,2.2vw,30px)}
.km-charthead{display:flex;justify-content:space-between;gap:16px;align-items:start;flex-wrap:wrap}
.km-charthead h3{font-size:20px;font-weight:700;letter-spacing:-.01em}
.km-chart{position:relative;margin-top:14px}
.km-chart svg{display:block;width:100%;height:auto;overflow:visible;touch-action:pan-y}
.km-chart text{font-family:var(--font);font-size:13px;fill:var(--ink2)}
.km-tip{position:absolute;top:0;pointer-events:none;background:var(--ink);color:#fff;border-radius:10px;padding:9px 13px;font-size:14px;line-height:1.45;white-space:nowrap;transform:translateX(-50%);z-index:3}
.km-legend{display:flex;flex-wrap:wrap;gap:8px 22px;margin-top:12px;font-size:14px;color:var(--ink2)}
.km-legend i{display:inline-block;width:20px;height:0;border-top:3px solid;vertical-align:middle;margin-right:8px}
.km-miles{display:grid;grid-template-columns:repeat(3,1fr);margin-top:20px;border-top:1px solid var(--line)}
.km-miles div{padding-top:14px}.km-miles dt{font-size:14px;color:var(--ink2)}.km-miles dd{font-size:22px;font-weight:700}
.km details>summary{cursor:pointer;font-weight:700;color:var(--brand);margin-top:18px;list-style:none;min-height:44px;display:flex;align-items:center}
.km details>summary::-webkit-details-marker{display:none}
.km details>summary::after{content:'';width:8px;height:8px;border:solid currentColor;border-width:0 2px 2px 0;transform:translateY(-2px) rotate(45deg);margin-left:12px;transition:transform .2s}
.km details[open]>summary::after{transform:translateY(2px) rotate(225deg)}

/* tables */
.km-tablewrap{overflow-x:auto;background:var(--paper);border:1px solid var(--line);border-radius:20px}
.km table{width:100%;border-collapse:collapse}
.km thead{background:var(--sunk2)}
.km th{font-size:14px;font-weight:600;color:var(--ink2);text-align:right;padding:16px 20px;border-bottom:1px solid var(--line);white-space:nowrap}
.km td{padding:17px 20px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
.km tr:last-child td{border-bottom:0}
.km th:first-child,.km td:first-child{text-align:left}
.km tbody tr:hover{background:var(--sunk)}
.km td strong{font-size:18px;font-weight:700}
.km-best{display:inline-block;margin-left:10px;font-size:13px;font-weight:700;color:var(--good);background:#e2f4ec;border-radius:6px;padding:2px 9px}
.km-bar{display:block;height:6px;border-radius:6px;background:var(--brand2);margin-top:8px;margin-left:auto;opacity:.85}

/* lots, deals */
.km-lots{display:grid;grid-template-columns:repeat(auto-fill,minmax(282px,1fr));gap:22px}
.km-lot{display:flex!important;flex-direction:column;background:var(--paper)!important;border:1px solid var(--line)!important;border-radius:18px;overflow:hidden;transition:border-color .2s,box-shadow .2s}
.km-lot:hover{border-color:var(--brand2)!important;box-shadow:0 16px 34px -20px rgba(36,18,11,.5)}
.km-lot figure{position:relative;height:176px;background:var(--sunk2);overflow:hidden;width:100%}
.km-lot img{width:100%;height:100%;object-fit:cover}
.km-state{position:absolute;left:12px;top:12px;background:rgba(255,255,255,.94);color:var(--ink);font-size:14px;font-weight:700;border-radius:8px;padding:4px 11px}
.km-lot .b{padding:18px 20px 20px;width:100%}
.km-lot h3{font-size:20px;font-weight:700;line-height:1.3}
.km-facts{display:flex;gap:28px;margin-top:14px!important}
.km-facts dt{font-size:14px;color:var(--ink2)}.km-facts dd{font-weight:700;font-size:17px}
.km-add{align-items:center;justify-content:center;text-align:center!important;min-height:300px;border-style:dashed!important;border-width:2px!important;border-color:var(--line2)!important;background:transparent!important;gap:10px;padding:28px!important}
.km-add b{font-size:19px;color:var(--brand)}
.km-banner{position:relative;isolation:isolate;background:var(--soil);color:#fff;overflow:hidden}
.km-banner img{position:absolute;inset:0;z-index:-2;width:100%;height:100%;object-fit:cover}
.km-banner::before{content:'';position:absolute;inset:0;z-index:-1;background:linear-gradient(90deg,rgba(26,12,7,.9),rgba(26,12,7,.55) 48%,rgba(26,12,7,.12))}
.km-banner .km-wrap{min-height:clamp(250px,34vh,330px);display:flex;flex-direction:column;justify-content:flex-end;padding-block:36px}
.km-banner h1{font-size:clamp(38px,4.6vw,62px);font-weight:800;letter-spacing:-.028em;line-height:1.12}
.km-banner p{color:#f4e3d8;max-width:56ch;margin-top:8px!important}
.km-deal{display:grid;grid-template-columns:200px 1fr;background:var(--paper);border:1px solid var(--line);border-radius:18px;overflow:hidden}
.km-deal+.km-deal{margin-top:20px}
.km-deal>img{width:100%;height:100%;object-fit:cover;min-height:170px}
.km-deal .b{padding:22px 26px}
.km-deal .top{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;align-items:start}
.km-steps{display:grid;grid-template-columns:repeat(4,1fr);margin-top:22px!important}
.km-steps li{position:relative;padding-top:24px;font-size:15px;color:var(--ink3);padding-right:8px}
.km-steps li::before{content:'';position:absolute;top:6px;left:0;right:0;height:3px;background:var(--line2)}
.km-steps li::after{content:'';position:absolute;top:0;left:0;width:15px;height:15px;border-radius:50%;background:var(--paper);border:3px solid var(--line2)}
.km-steps li.on{color:var(--ink);font-weight:600}.km-steps li.on::before{background:var(--good)}.km-steps li.on::after{background:var(--good);border-color:var(--good)}
.km-steps li:last-child::before{right:auto;width:15px}
.km-quote{margin-top:14px!important;padding-left:14px!important;border-left:3px solid var(--line2);color:var(--ink2)}
.km-empty{text-align:center;padding:64px 20px;background:var(--paper);border:1px solid var(--line);border-radius:20px}
.km-skel{background:linear-gradient(90deg,var(--sunk2),var(--sunk),var(--sunk2));background-size:200% 100%;animation:kmsk 1.4s linear infinite;border-radius:16px}

/* footer */
.km-foot{background:var(--soil);color:#e9d8cd;padding-block:44px 52px}
.km-foot nav{display:flex;flex-wrap:wrap;gap:6px 28px;margin:22px 0}
.km-foot nav button{min-height:40px;font-weight:600}.km-foot nav button:hover{color:#fff;text-decoration:underline;text-underline-offset:5px}
.km-foot p{font-size:14px;color:#c9b2a4;max-width:80ch}
.km-btn[data-glass]{background:rgba(255,255,255,.14)!important;box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.45)}
.km-btn[data-glass]:hover{background:rgba(255,255,255,.24)!important}

/* assistant */
.km-fab{position:fixed!important;right:clamp(16px,2.4vw,32px);bottom:clamp(16px,2.4vw,32px);z-index:80;display:flex!important;align-items:center;gap:14px;background:var(--brand)!important;color:#fff!important;border-radius:999px;padding:8px 26px 8px 8px!important;font-weight:700;font-size:17px;box-shadow:0 16px 36px -10px rgba(110,32,0,.65);transition:transform .22s var(--ease),background .2s}
.km-fab:hover{transform:translateY(-2px);background:var(--brand2)!important}
.km-face{width:48px;height:48px;border-radius:50%;object-fit:cover;flex:none;background:var(--soil)}
.km-chat{position:fixed;right:clamp(12px,2.4vw,32px);bottom:clamp(12px,2.4vw,32px);z-index:90;width:min(440px,calc(100vw - 24px));height:min(720px,calc(100dvh - 110px));display:flex;flex-direction:column;background:var(--bg);border-radius:24px;overflow:hidden;box-shadow:0 32px 80px -16px rgba(36,18,11,.5),0 0 0 1px rgba(36,18,11,.08);animation:kmup .32s var(--ease) both;transform-origin:100% 100%}
.km-chat.full{position:static;width:100%;max-width:860px;height:100%;margin:0 auto;border-radius:0;box-shadow:none;animation:none;background:transparent}
.km-chat header{position:relative;isolation:isolate;color:#fff;padding:18px 20px;display:flex;align-items:center;gap:14px;background:var(--soil);flex:none}
.km-chat header>img.bgi{position:absolute;inset:0;z-index:-2;width:100%;height:100%;object-fit:cover}
.km-chat header::before{content:'';position:absolute;inset:0;z-index:-1;background:linear-gradient(90deg,rgba(26,12,7,.88),rgba(26,12,7,.5))}
.km-chat header b{font-size:18px;display:block;line-height:1.3}.km-chat header small{font-size:14px;color:#f4e3d8}
.km-chat header button{width:44px;height:44px;display:grid;place-items:center;border-radius:12px}
.km-chat header button:hover{background:rgba(255,255,255,.16)}
.km-log{flex:1;min-height:0;overflow-y:auto;padding:22px 20px;display:flex;flex-direction:column;gap:18px}
.km-say{font-size:17px;line-height:1.55}
.km-turn{animation:kmin .28s var(--ease) both}
.km-turn.me{align-self:flex-end;max-width:84%;background:var(--brand);color:#fff;border-radius:18px 18px 4px 18px;padding:11px 17px;font-size:17px}
.km-hello{font-size:28px;font-weight:800;letter-spacing:-.02em;line-height:1.2}
.km-asks{display:grid;gap:10px;margin-top:20px}
.km-asks button{display:flex;align-items:center;gap:14px;background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:9px 16px 9px 9px;font-weight:600;min-height:66px;transition:border-color .18s}
.km-asks button:hover{border-color:var(--brand2)}
.km-asks img{width:48px;height:48px;border-radius:11px;object-fit:cover;flex:none}
.km-card{margin-top:12px;background:var(--paper);border:1px solid var(--line);border-radius:18px;overflow:hidden}
.km-card .ph{position:relative;height:112px;background:var(--soil);color:#fff}
.km-card .ph img{width:100%;height:100%;object-fit:cover}
.km-card .ph div{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:flex-end;padding:13px 18px;background:linear-gradient(90deg,rgba(26,12,7,.86),rgba(26,12,7,.1))}
.km-card .ph b{font-size:22px;line-height:1.2}.km-card .ph span{font-size:14px}
.km-card .in{padding:16px 18px 18px}
.km-card .km-pair{margin-top:12px}.km-card .km-pair{gap:10px}.km-card .km-pair>div{padding:12px 14px}.km-card .km-pair dd{font-size:26px}
.km-acts{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px;align-items:center}
.km-acts .km-btn{min-height:44px;padding:0 18px!important;font-size:15px}
.km-chips{display:flex;gap:8px;overflow-x:auto;padding:0 20px 12px;flex:none;scrollbar-width:none}
.km-chips button{flex:none;min-height:42px;padding:0 16px;border-radius:999px;background:var(--paper);border:1px solid var(--line2);font-weight:600;font-size:15px}
.km-chips button:hover{border-color:var(--brand2);color:var(--brand)}
.km-ask{flex:none;display:flex;gap:10px;align-items:end;padding:12px 16px 16px;background:var(--paper);border-top:1px solid var(--line)}
.km-ask textarea{flex:1;resize:none;min-height:52px;max-height:120px;border-radius:16px;border:1.5px solid var(--line2);background:var(--bg);padding:13px 17px;font-size:17px;line-height:1.4}
.km-ask textarea:focus{outline:0;border-color:var(--brand2)}
.km-rnd{width:52px;height:52px;border-radius:50%;display:grid!important;place-items:center;background:var(--brand2)!important;color:#fff!important;flex:none}
.km-rnd:hover{background:var(--brand)!important}.km-rnd.live{animation:kmring 1.3s ease-out infinite}.km-rnd[disabled]{opacity:.45}
.km-think{display:inline-flex;gap:6px;align-items:center;color:var(--ink2);font-size:15px}
.km-think i{width:8px;height:8px;border-radius:50%;background:var(--brand2);animation:kmdot 1.1s infinite}.km-think i:nth-child(2){animation-delay:.14s}.km-think i:nth-child(3){animation-delay:.28s;margin-right:6px}

/* inner steps: forms and details get a readable column, not the full window */
@keyframes kmfade{from{opacity:0;transform:scale(1.035)}}
@keyframes kmup{from{opacity:0;transform:translateY(18px) scale(.97)}}
@keyframes kmin{from{opacity:0;transform:translateY(8px)}}
@keyframes kmsk{to{background-position:-200% 0}}
@keyframes kmdot{0%,60%,100%{opacity:.25}30%{opacity:1}}
@keyframes kmring{from{box-shadow:0 0 0 0 rgba(194,65,12,.5)}to{box-shadow:0 0 0 16px rgba(194,65,12,0)}}
@media (max-width:980px){
  .km-advice{grid-template-columns:minmax(0,1fr)!important}
  .km-nav .km-wrap{height:62px}
  .km-me>button span:last-child{display:none}
  .km-tabs{position:fixed;inset:auto 0 0;height:66px;background:var(--paper);border-top:1px solid var(--line);z-index:70;justify-content:space-around;padding:0 4px}
  .km-tabs button{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;font-size:13px;padding:0 6px;flex:1}
  .km-tabs button svg{display:block}
  .km-tabs button[aria-current=page]::after{top:0;bottom:auto;border-radius:0 0 3px 3px}
  .km-brand{margin-right:auto!important}
  .km-page{padding-bottom:66px}
  .km-fab{bottom:80px}
}
@media (max-width:620px){
  .km-brand span{display:none}
  .km-deal{grid-template-columns:1fr}.km-deal>img{height:140px;min-height:0}
  .km-steps{grid-template-columns:1fr;gap:4px}.km-steps li{padding:0 0 14px 28px}.km-steps li::before{left:6px!important;right:auto!important;width:3px!important;top:0;height:100%}.km-steps li:last-child::before{height:0}
  .km-chat{inset:0;width:100%;height:100dvh;border-radius:0}
  .km-hidem{display:none}
  .km th,.km td{padding:14px 14px}
}
@media (prefers-reduced-motion:reduce){.km *,.km{animation:none!important;transition:none!important}}
`;

export function ensureCss() {
  if (typeof document === 'undefined') return;
  let el = document.getElementById('km-css');
  if (!el) {
    el = document.createElement('style');
    el.id = 'km-css';
    document.head.appendChild(el);
  }
  if (el.textContent !== CSS) el.textContent = CSS;
}
ensureCss();
