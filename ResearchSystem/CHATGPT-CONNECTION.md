# Connect the private book MCP to ChatGPT

Local preparation: official OpenAI tunnel-client v0.0.21 for Windows amd64 is
installed under ignored `data/tunnel-client/bin/`. Its archive SHA-256 matches
the official release checksum. Local MCP search/fetch/list_books have passed
against the real book database. End-to-end setup still requires the account
steps below and a successful live tool call; local tests alone are insufficient.

## Account setup

1. Open https://platform.openai.com/settings/organization/tunnels using your
   intended OpenAI account. Create or reuse a tunnel named MGCA Book Research.
   Associate it with the ChatGPT workspace where you will test it. Copy its
   `tunnel_id`. Creating a tunnel requires Tunnels Read + Manage.
2. Create a restricted runtime key at
   https://platform.openai.com/settings/organization/api-keys with Tunnels
   Read + Use. Use a runtime key, not an admin key. Enter it only into the
   launcher's hidden local prompt; never paste it into chat or commit it. The
   Windows launcher saves it using DPAPI tied to the Windows account/computer.
3. In a PowerShell terminal in this project run:

   ```powershell
   .\Connect-ChatGPT.ps1
   ```

   Enter the tunnel ID and runtime key on first use. Future launches reuse the
   saved tunnel ID and encrypted credential without prompting. Keep the terminal open.
   It starts the actual real-book MCP over stdio through the private tunnel;
   no separate HTTP server, public hostname or inbound port forwarding is needed.
4. Read `data/tunnel-client/health.url`, then open that local URL with `/ui`
   appended. Check readiness and polling before adding the server in ChatGPT.
5. Open https://chatgpt.com/plugins, select **+ > Add custom MCP server**, name
   it **MGCA Book Research**, choose **Connection: Tunnel**, and select the
   same tunnel. This local server has no additional OAuth login; access is
   controlled by the private tunnel and its account/workspace association.
   Review the displayed tools and create/install your private plugin.
6. Open the installed **MGCA Book Research** plugin and select **Try in chat**,
   then ask:

   > List my indexed books. Then search for time dilation and Lorentz
   > transformations, fetch the relevant passages, and compare explanations
   > from two books. Include source locations and flag extraction problems.

Successful local tests alone do not prove the ChatGPT connection. Completion
requires a successful tool call from the ChatGPT conversation.

## Saved key and restart

`data/tunnel-client/runtime-key.dpapi` contains the Windows-protected credential;
`data/tunnel-client/connection.json` stores the non-secret tunnel ID. Both are
excluded from Git. No plaintext key is written to disk. Copying the encrypted
credential to another machine/account is not a portable credential backup.

```powershell
.\Connect-ChatGPT.ps1                 # reuse the saved key and tunnel ID
.\Connect-ChatGPT.ps1 -ReplaceKey     # hidden prompt for a replacement
.\Connect-ChatGPT.ps1 -SaveKeyOnly    # verify/save locally without starting the tunnel
```

Saving a key does not extend its expiry or undo revocation. Replace it when
the account-side credential expires or is revoked. Existing foreground clients
continue running; launcher updates apply the next time they are started.

## Official references

- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
- https://github.com/openai/tunnel-client/releases/latest

The current help article states that Pro users can connect custom MCP servers
with read/fetch permissions. Account rollout and workspace permissions still
need checking in the actual signed-in interface.
