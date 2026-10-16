This document presents the API of PaygOps, designed to enable integration between third-party tools and PaygOps. PaygOps operates on a modular architecture, allowing clients to selectively use and pay for specific features (or microservices), such as Leads, One-Off Payments, Credit & Subscription Payments, and Ticketing. This flexible approach ensures that PaygOps can easily fit in and complement your existing workflows and tools.


# Introduction
## HTTPS with TLS v1.2+, transport layer security

The connection to the platform must be secured by HTTPS using TLS v1.2 or TLS v1.3, the system will try to use the newest version and fallback to an older version if not supported. The supported cipher suites are EECDH+AESGCM, EDH+AESGCM, EECDH+AES256, EDH+AES256.

## JWT Key, request origin and permission verification

The HTTP request header must include a valid JWT key provided in the “Authorization” header and preceded by the keywork “Bearer” and a space. For example: 

Authorization: Bearer xxxxxxx.yyyyyyyyy.zzzzzzz

The JWT key can be obtained from the owner of the PaygOps instance and will be valid only for that instance and for a specific time duration (we recommend renewing it every few months). 

Important: In case of a security breach on your server, compromising the JWT key, the JWT can be blacklisted on the PaygOps and will not be valid anymore. 

## Encoding rules (JSON)

All content exchanged with the API needs to be in JSON format as defined by RFC-8259. 

Date and datetimes needs exchanged must be in the format specified by ISO 8601 (compatible with RFC3339). 

# Performance and responsible use

While the use of APIs offer a lot of possibilities, it is important to use them in a responsible way in order to maintain good performance of the platform for regular users. 

## Overall usage

PaygOps instances are sized for a maximum of 500 object requests per active contract per month (including both Web app, Mobile App, Integrations and API). For the API, it is recommended to stay below 100 object requests per active contract per month to ensure optimal performance of the platform. One object request correpond to either one request to a single object (e.g. create one new lead, get one client, etc.) or to a single object within a multi-object API request (e.g. getting a page of 1000 leads with `include_objects` corresponds to 1000 object requests). 

**IMPORTANT:** This value is provided as an indicative absolute upper limit assuming requests are spread evenly through the month. It is recommended to design integrations to stay well below that limit as approaching the limit already affects performance negatively. **While this limit is not currently enforced, it might be enforced at any point in the future. Get in touch with Customer Success if you think your needs might exceed the limit.**

It is important to keep those number in minds when designing integrations. For example, if you iterate through all contracts once a day, it will result in 30 object requests per contract per month (for a 30 day month) or 300,000 requests for 10,000 contracts. This would be acceptable and leave room to perform other operations like editing leads, etc. However, if you iterate through all contracts every hour, it will result in 720 object requests (30 days * 24 hours) per contract per month (or 7,200,000 requests for 10,000 contracts) which would exceed the limit and not be acceptable, resulting in impaired performance for users. 

## Bulk usage

It is recommended to spread API calls as much as possible. If you need to run bulk operations (e.g. iterating through all contracts), you should follow the following guidelines: 

1. Try to run the bulk operations at night or during periods of low usage by users

2. Always use multi-object requests when possible (e.g. get contracts by pages of 100 to 1000 with `include_objects` when processing all contracts, rather than getting them one by one)

3. Do not run large requests at the same time (e.g. do not try to get 1000 contracts and 1000 leads at the same time)

4. Leave a gap between each large multi-object requests (e.g. leave 1s between each page)

5. Request only what you really need. For example instead of requesting the whole list of payments daily, use the `from_date` parameter to get only new the payments since your last request and save the list on your server every time. 

6. Consider using Web Hooks to get data as it is created or updated. You can for example get a request to your server with the details of new payment every time one is received on PaygOps, completely removing the need to use the list at regular intervals. 

## Use of lists

When using lists, it is highly recommended to use pagination as a general rule, even when just querying IDs. In the case where you get the objects in the list and not just their IDs, you then **MUST** use pagination. The maximum page size when using `include_objects` is 1000, although it is recommended to use a smaller page size (e.g. 250), especially when using APIs returning a lot of object data (e.g. contracts). When using the `include_subobjects` parameters in addition, the maximum page size drops to 250. 

**IMPORTANT:** While these limits on page_size are not currently enforced, after **March 31st 2022**, trying to query a list with `include_objects` (or `include_subobjects`) but without a `page` or with a `page_size` over the limit will result in an error message explaining the limit. 

