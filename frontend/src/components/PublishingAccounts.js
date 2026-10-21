import React from "react";

export function PublishingAccounts({ connections, busy, onConnect, onDisconnect }) {
  return <section className="space-y-3" aria-label="Connected publishing accounts">
    <h3 className="font-semibold">Creator accounts</h3>
    {connections.platforms.map(platform => {
      const accounts = connections.accounts.filter(account => account.platform === platform.id);
      return <div key={platform.id} className="rounded-xl border border-gray-200 p-3 dark:border-gray-700">
        <div className="flex items-center justify-between gap-3">
          <span className="font-medium">{platform.name}</span>
          <button type="button" disabled={busy || !platform.configured} onClick={() => onConnect(platform.id)} className="text-sm font-medium text-blue-600 disabled:text-gray-400">
            {accounts.length ? "Connect another account" : "Connect account"}
          </button>
        </div>
        {platform.setup_message && <p className="mt-1 text-xs text-gray-500">{platform.setup_message}</p>}
        {platform.id === "instagram" && <p className="mt-1 text-xs text-gray-500">Use a Business or Creator account linked to a Facebook Page.</p>}
        {platform.id === "tiktok" && <p className="mt-1 text-xs text-gray-500">Public posting requires TikTok to approve the app. During testing, the app owner must add your TikTok account to the sandbox's Target users before you can connect.</p>}
        {accounts.map(account => <div key={account.id} className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm">
          <div>
            <p>{account.display_name}</p>
            <p className={`text-xs ${account.needs_reconnect ? "text-amber-700 dark:text-amber-400" : "text-gray-500"}`}>
              {account.needs_reconnect ? "Reconnect required" : "Connected"}
            </p>
          </div>
          <div className="flex gap-3">
            <button type="button" disabled={busy || !platform.configured} onClick={() => onConnect(platform.id)} className="text-blue-600 underline disabled:text-gray-400" aria-label={`Reconnect ${account.display_name}`}>Reconnect</button>
            <button type="button" disabled={busy} onClick={() => onDisconnect(account.id)} className="text-gray-500 underline" aria-label={`Disconnect ${account.display_name}`}>Disconnect</button>
          </div>
        </div>)}
      </div>;
    })}
  </section>;
}
