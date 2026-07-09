# Social Media Platform Credentials - Configuration Guide

## Status Overview

| Platform | Status | Credentials Obtained |
|----------|--------|---------------------|
| X/Twitter | DONE | Bearer Token, OAuth2 Client ID + Secret |
| Facebook/Meta | PENDING | Need to complete developer registration |
| LinkedIn | PENDING | Need to create developer app |
| TikTok | PENDING | Need to create developer app |
| YouTube | PENDING | Need Google Cloud OAuth2 setup |

---

## 1. X/Twitter - COMPLETED

### Obtained Credentials

| Secret Name | Value |
|-------------|-------|
| `TWITTER_BEARER_TOKEN` | `AAAAAAAAAAAAAAAAAAAAANrX9wEAAAAA%2Br29KmWJG2I9O3NpdZT%2Baa6lctw%3DnxZQdDYwAlwmhzzwnQaqEUK5oQ6kZRxU28fXwx8U0CbSyTg9An` |
| `TWITTER_OAUTH2_CLIENT_ID` | `enFKN1doMjhNd0ZLLXhXb3ZQOFQ6MTpjaQ` |
| `TWITTER_OAUTH2_CLIENT_SECRET` | `_a0Ku3QO4ogq07XkzDtesFq_MG9RHIG2ej3Rbtn4sQNSekNy7Y` |

### App Configuration
- **App Name**: 2062445667465785344fys2388
- **App ID**: 33019866
- **App Permissions**: Read and Write
- **App Type**: Web App, Automated App or Bot (Confidential client)
- **Callback URI**: https://chinaboundtravel.com/callback
- **Website URL**: https://chinaboundtravel.com
- **Console URL**: https://console.x.com/accounts/2062445667465785344/apps/33019866

### GitHub Secrets to Add
Go to: https://github.com/fys2388/chinabound-travel/settings/secrets/actions

```
TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAANrX9wEAAAAA%2Br29KmWJG2I9O3NpdZT%2Baa6lctw%3DnxZQdDYwAlwmhzzwnQaqEUK5oQ6kZRxU28fXwx8U0CbSyTg9An
TWITTER_OAUTH2_CLIENT_ID=enFKN1doMjhNd0ZLLXhXb3ZQOFQ6MTpjaQ
TWITTER_OAUTH2_CLIENT_SECRET=_a0Ku3QO4ogq07XkzDtesFq_MG9RHIG2ej3Rbtn4sQNSekNy7Y
```

---

## 2. Facebook/Meta - TODO

### Steps to Complete
1. Go to https://developers.facebook.com and complete developer registration (phone verification required)
2. After registration, go to https://developers.facebook.com/apps/ and click "Create App"
3. Select **Business** type, choose **Facebook Login** product
4. Fill in App Name: "ChinaBound Travel Bot", Contact Email: your email
5. In App Dashboard → Settings → Basic, note the **App ID** and **App Secret**
6. Add Facebook Login product, configure OAuth redirect URI: `https://chinaboundtravel.com/callback`
7. Go to Facebook Page → Settings → Connected Apps → Add your app
8. Generate a **Page Access Token** with `pages_manage_posts,pages_read_engagement` permissions
9. Note your **Facebook Page ID** (found in Page → About → Page ID)

### GitHub Secrets to Add
```
FACEBOOK_PAGE_ID=<your_page_id>
FACEBOOK_PAGE_ACCESS_TOKEN=<your_page_access_token>
```

---

## 3. LinkedIn - TODO

### Steps to Complete
1. Go to https://www.linkedin.com/developers/apps and click "Create App"
2. Fill in App Name: "ChinaBound Travel Bot", LinkedIn Page URL, Company Email
3. In Auth tab, note **Client ID** and **Client Secret**
4. Add redirect URL: `https://chinaboundtravel.com/callback`
5. Request product: **Sign In with LinkedIn using OpenID Connect**
6. In products tab, add **Marketing Developer Platform** → **Share on LinkedIn** → **UGC Posts API**
7. Generate an **Access Token** with `w_member_social` and `r_liteprofile` scopes
8. Find your **Company URN** from LinkedIn Page (e.g., `urn:li:organization:12345678`)

### GitHub Secrets to Add
```
LINKEDIN_ACCESS_TOKEN=<your_access_token>
LINKEDIN_CLIENT_ID=<your_client_id>
LINKEDIN_CLIENT_SECRET=<your_client_secret>
LINKEDIN_COMPANY_URN=<your_company_urn>
```

---

## 4. TikTok - TODO

### Steps to Complete
1. Go to https://developers.tiktok.com/apps and create a new app
2. Select **Manage multiple TikTok accounts via API**
3. In App configuration → Key Management, note **Client Key** and **Client Secret**
4. Add redirect URI: `https://chinaboundtravel.com/callback`
5. Request **Content Posting API** permission (requires app review)
6. Generate an **Access Token** with `video.upload` scope
7. Note your **TikTok Business Account ID**

### GitHub Secrets to Add
```
TIKTOK_ACCESS_TOKEN=<your_access_token>
TIKTOK_CLIENT_KEY=<your_client_key>
TIKTOK_CLIENT_SECRET=<your_client_secret>
```

---

## 5. YouTube - TODO

### Steps to Complete
1. Go to https://console.cloud.google.com/ and create a project "ChinaBound Travel"
2. Enable **YouTube Data API v3** in APIs & Services
3. Go to Credentials → Create OAuth 2.0 Client ID
4. Select "Web application", add redirect URI: `https://chinaboundtravel.com/callback`
5. Note **Client ID** and **Client Secret**
6. Go to OAuth 2.0 Playground: https://developers.google.com/oauthplayground/
7. Use your Client ID/Secret, authorize with scopes: `https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube`
8. Exchange authorization code for **Refresh Token**
9. Create a JSON file with Client ID, Client Secret, and Refresh Token

### GitHub Secrets to Add
```
YOUTUBE_CLIENT_ID=<your_client_id>
YOUTUBE_CLIENT_SECRET=<your_client_secret>
YOUTUBE_OAUTH_REFRESH_TOKEN=<your_refresh_token>
```

---

## Notes

- All credentials should be added as **GitHub Actions Secrets** at: https://github.com/fys2388/chinabound-travel/settings/secrets/actions
- The `social_distributor.yml` workflow reads these secrets as environment variables
- X/Twitter Bearer Token is URL-encoded. The `%2B` is `+` and `%3D` is `=`
- Facebook Page Access Token never expires if you use a System User token (recommended)
- LinkedIn Access Tokens expire in 60 days - use a refresh mechanism
- YouTube Refresh Token is long-lived - preferred over access tokens
