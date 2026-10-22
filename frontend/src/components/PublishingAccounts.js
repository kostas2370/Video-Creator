import React from "react";
import { SiYoutube, SiTiktok, SiInstagram } from "react-icons/si";
import { HiOutlineLink } from "react-icons/hi2";

const platformStyle = {
  youtube: { icon: SiYoutube, color: "bg-red-50 text-red-600 dark:bg-red-950/40 dark:text-red-400", description: "Publish your videos to your YouTube channels." },
  tiktok: { icon: SiTiktok, color: "bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-white", description: "Share your videos with your TikTok audience." },
  instagram: { icon: SiInstagram, color: "bg-pink-50 text-pink-600 dark:bg-pink-950/40 dark:text-pink-400", description: "Publish Reels to your professional Instagram accounts." },
};
const secondary = "min-h-11 rounded-xl border border-gray-200 px-3 py-2 text-sm font-medium hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50 dark:border-gray-600 dark:hover:bg-gray-700";

export function PublishingAccounts({ connections, busy, onConnect, onDisconnect }) {
  return <section className="grid gap-x-5 lg:grid-cols-3" aria-label="Connected publishing accounts">
    {connections.platforms.map(platform => {
      const accounts = connections.accounts.filter(account => account.platform === platform.id);
      const style = platformStyle[platform.id];
      const Icon = style?.icon || HiOutlineLink;
      return <article key={platform.id} className="mb-5 grid min-w-0 lg:mb-0 grid-rows-[auto_1fr_auto_auto] lg:row-span-4 lg:grid-rows-subgrid rounded-2xl border border-gray-200 bg-white p-5 sm:p-6 dark:border-gray-700 dark:bg-gray-800">
        <header>
          <div className={`mb-5 flex h-12 w-12 items-center justify-center rounded-2xl ${style?.color || "bg-blue-50 text-blue-600"}`}><Icon aria-hidden="true" className="h-6 w-6" /></div>
          <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-semibold">{platform.name}</h2><span className={`rounded-full px-2.5 py-1 text-xs font-medium ${!platform.configured ? "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300" : accounts.some(account => account.needs_reconnect) ? "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-300" : accounts.length ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"}`}>{!platform.configured ? "Setup needed" : accounts.some(account => account.needs_reconnect) ? "Needs attention" : accounts.length ? "Connected" : "Not connected"}</span></div>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{style?.description}</p>
        </header>
        <ul className="my-5 space-y-4">
          {accounts.map(account => <li key={account.id} className="border-t border-gray-100 pt-4 dark:border-gray-700">
            <p className="break-words text-sm font-semibold">{account.display_name}</p>
            <p className={`mt-1 text-xs ${account.needs_reconnect ? "text-amber-700 dark:text-amber-400" : "text-gray-500 dark:text-gray-400"}`}>{account.needs_reconnect ? "Reconnect required to publish" : "Ready to publish"}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" disabled={!!busy || !platform.configured} onClick={() => onConnect(platform.id)} className={secondary} aria-label={`Reconnect ${account.display_name}`}>Reconnect</button>
              <button type="button" disabled={!!busy} onClick={() => onDisconnect(account)} className={`${secondary} text-gray-500 dark:text-gray-300`} aria-label={`Disconnect ${account.display_name}`}>Disconnect</button>
            </div>
          </li>)}
        </ul>
        <button type="button" disabled={!!busy || !platform.configured} onClick={() => onConnect(platform.id)} className="min-h-11 w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-40">{busy === platform.id ? "Opening connection…" : accounts.length ? "Connect another account" : `Connect ${platform.name}`}</button>
        <div className="text-sm">
        {platform.setup_message && <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">{platform.setup_message}</p>}
        {platform.id === "instagram" && <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">Requires a Business or Creator account linked to a Facebook Page.</p>}
        {platform.id === "tiktok" && <details className="mt-3 text-xs text-gray-500 dark:text-gray-400"><summary className="cursor-pointer py-2">Testing and publishing access</summary><p className="mt-1">Public posting requires TikTok to approve the app. During testing, connect a sandbox Target user, set your TikTok account to private, and choose “Only me” visibility when posting.</p></details>}
        </div>
      </article>;
    })}
  </section>;
}
