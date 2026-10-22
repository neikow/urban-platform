# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/neikow/urban-platform/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                           |    Stmts |     Miss |   Branch |   BrPart |      Cover |   Missing |
|--------------------------------------------------------------- | -------: | -------: | -------: | -------: | ---------: | --------: |
| about/\_\_init\_\_.py                                          |        0 |        0 |        0 |        0 |    100.00% |           |
| about/apps.py                                                  |        4 |        0 |        0 |        0 |    100.00% |           |
| about/blocks.py                                                |       53 |        0 |        0 |        0 |    100.00% |           |
| about/management/\_\_init\_\_.py                               |        0 |        0 |        0 |        0 |    100.00% |           |
| about/management/commands/\_\_init\_\_.py                      |        0 |        0 |        0 |        0 |    100.00% |           |
| about/management/commands/populate\_about\_pages.py            |       19 |       19 |        6 |        0 |      0.00% |      1-32 |
| about/models/\_\_init\_\_.py                                   |        5 |        0 |        0 |        0 |    100.00% |           |
| about/models/about\_commission.py                              |       17 |        0 |        0 |        0 |    100.00% |           |
| about/models/about\_dev\_team.py                               |       17 |        0 |        0 |        0 |    100.00% |           |
| about/models/about\_index.py                                   |       14 |        0 |        0 |        0 |    100.00% |           |
| about/models/about\_website.py                                 |       16 |        0 |        0 |        0 |    100.00% |           |
| about/page\_templates.py                                       |       15 |        0 |        0 |        0 |    100.00% |           |
| core/\_\_init\_\_.py                                           |        0 |        0 |        0 |        0 |    100.00% |           |
| core/admin\_dashboard.py                                       |      105 |        0 |       10 |        2 |     98.26% |45-\>exit, 60-\>68 |
| core/admin\_menu.py                                            |       53 |        2 |        8 |        2 |     93.44% |   72, 111 |
| core/apps.py                                                   |       35 |        0 |        2 |        0 |    100.00% |           |
| core/area\_index.py                                            |       85 |        1 |       32 |        1 |     98.29% |        54 |
| core/association\_import.py                                    |       64 |        1 |       20 |        1 |     97.62% |68, 108-\>107 |
| core/associations.py                                           |      108 |        0 |       28 |        1 |     99.26% |215-\>exit |
| core/audit.py                                                  |      168 |       37 |       36 |        3 |     76.47% |50-51, 70-71, 83-84, 93-95, 104, 111-113, 128-129, 136-139, 146, 153-156, 163-166, 173-180, 242, 277 |
| core/auth\_backends.py                                         |       31 |        2 |        8 |        2 |     89.74% |  103, 106 |
| core/blocks.py                                                 |      182 |        0 |        4 |        2 |     98.92% |255-\>265, 262-\>265 |
| core/cache.py                                                  |       16 |        2 |        2 |        1 |     83.33% |33-34, 40-\>exit |
| core/content\_transfer/\_\_init\_\_.py                         |        0 |        0 |        0 |        0 |    100.00% |           |
| core/content\_transfer/archive.py                              |      167 |       17 |       80 |       13 |     87.85% |122, 143, 151, 158, 228, 235, 238, 242-243, 245, 260-261, 271, 274, 280, 282, 297 |
| core/content\_transfer/exporter.py                             |       81 |        6 |       18 |        3 |     90.91% |125-\>117, 136-137, 156-157, 177-178 |
| core/content\_transfer/importer.py                             |      163 |       10 |       50 |        6 |     90.61% |117-119, 131-\>exit, 168-169, 211, 219, 240-241, 249 |
| core/content\_transfer/jobs.py                                 |       56 |        4 |        8 |        1 |     92.19% |34-37, 75-\>77 |
| core/context\_processors.py                                    |        6 |        0 |        0 |        0 |    100.00% |           |
| core/data\_export.py                                           |       41 |        0 |        2 |        0 |    100.00% |           |
| core/emails/\_\_init\_\_.py                                    |        0 |        0 |        0 |        0 |    100.00% |           |
| core/emails/backend.py                                         |       30 |        1 |       16 |        4 |     89.13% |21-\>25, 23-\>22, 26, 38-\>36 |
| core/emails/services.py                                        |       50 |        3 |        4 |        1 |     92.59% |27, 79, 118 |
| core/emails/tasks.py                                           |       89 |       16 |        6 |        1 |     82.11% |44-48, 81-85, 124, 148-152 |
| core/emails/tokens.py                                          |       46 |        3 |        6 |        1 |     92.31% | 58, 61-62 |
| core/geocoding.py                                              |       64 |        2 |       10 |        2 |     94.59% |   66, 109 |
| core/helloasso.py                                              |       69 |        5 |        4 |        0 |     93.15% |59-60, 63-65 |
| core/management/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100.00% |           |
| core/management/commands/export\_content.py                    |       13 |        0 |        0 |        0 |    100.00% |           |
| core/management/commands/import\_associations.py               |       31 |        1 |        8 |        2 |     92.31% |37, 48-\>52, 52-\>exit |
| core/management/commands/import\_content.py                    |       16 |        2 |        0 |        0 |     87.50% |     34-35 |
| core/membership\_payments.py                                   |       87 |        5 |       30 |        5 |     91.45% |75, 101-\>109, 110-\>120, 129-\>131, 149-152 |
| core/membership\_reminders.py                                  |       33 |        2 |        6 |        0 |     94.87% |     69-70 |
| core/memberships.py                                            |      127 |        2 |       12 |        3 |     96.40% |37-\>45, 92, 100 |
| core/models/\_\_init\_\_.py                                    |       14 |        0 |        0 |        0 |    100.00% |           |
| core/models/announcement.py                                    |       26 |        0 |        0 |        0 |    100.00% |           |
| core/models/city.py                                            |        5 |        1 |        0 |        0 |     80.00% |         8 |
| core/models/city\_district.py                                  |       10 |        0 |        0 |        0 |    100.00% |           |
| core/models/city\_neighborhood.py                              |       15 |        2 |        0 |        0 |     86.67% |    18, 22 |
| core/models/content\_transfer.py                               |       49 |        1 |        0 |        0 |     97.96% |        89 |
| core/models/email\_event.py                                    |       31 |        0 |        0 |        0 |    100.00% |           |
| core/models/feature\_flags.py                                  |       18 |        0 |        4 |        0 |    100.00% |           |
| core/models/membership.py                                      |       57 |        0 |        4 |        0 |    100.00% |           |
| core/models/membership\_payment.py                             |       27 |        0 |        0 |        0 |    100.00% |           |
| core/models/membership\_reminder.py                            |       16 |        1 |        0 |        0 |     93.75% |        28 |
| core/models/neighborhood\_association.py                       |       32 |        0 |        0 |        0 |    100.00% |           |
| core/models/notification\_dispatch.py                          |       16 |        1 |        0 |        0 |     93.75% |        27 |
| core/models/task\_run.py                                       |       30 |        0 |        2 |        0 |    100.00% |           |
| core/models/user.py                                            |      124 |        4 |       10 |        3 |     94.78% |49, 64, 175, 222 |
| core/notifications/\_\_init\_\_.py                             |       16 |        0 |        0 |        0 |    100.00% |           |
| core/notifications/recipients.py                               |        6 |        0 |        0 |        0 |    100.00% |           |
| core/notifications/tasks.py                                    |       40 |        6 |        6 |        1 |     84.78% | 71-75, 80 |
| core/notifications/tokens.py                                   |       11 |        0 |        0 |        0 |    100.00% |           |
| core/page\_templates.py                                        |       48 |        0 |       10 |        0 |    100.00% |           |
| core/permissions.py                                            |       16 |        0 |        8 |        0 |    100.00% |           |
| core/roles.py                                                  |       23 |        0 |        6 |        1 |     96.55% |   51-\>53 |
| core/sitemaps.py                                               |       72 |       21 |        6 |        0 |     65.38% |31-33, 36, 39, 47, 55-65, 73, 81, 89, 97, 105, 113-122 |
| core/task\_monitor.py                                          |      144 |        8 |       22 |        2 |     93.98% |82-83, 92-93, 151-152, 205, 214 |
| core/tasks.py                                                  |       33 |        9 |        2 |        1 |     71.43% |23-25, 31-33, 39-41, 52, 59-61 |
| core/templatetags/\_\_init\_\_.py                              |        0 |        0 |        0 |        0 |    100.00% |           |
| core/templatetags/announcement\_tags.py                        |       16 |        0 |        6 |        0 |    100.00% |           |
| core/templatetags/custom\_blocks.py                            |       18 |        7 |        8 |        3 |     53.85% |11, 13, 16-19, 24-39 |
| core/templatetags/django\_settings.py                          |        6 |        0 |        0 |        0 |    100.00% |           |
| core/templatetags/forms.py                                     |        6 |        0 |        0 |        0 |    100.00% |           |
| core/templatetags/navigation\_tags.py                          |       53 |        3 |       18 |        4 |     90.14% |22-\>25, 36, 48, 53 |
| core/templatetags/social\_meta.py                              |       28 |        0 |        8 |        1 |     97.22% |   50-\>52 |
| core/templatetags/structured\_data.py                          |      113 |        4 |       42 |       10 |     90.97% |30-31, 90-\>93, 100, 133-\>138, 135-\>138, 154-\>157, 162-\>165, 166-\>169, 173-\>189, 181-\>187, 200 |
| core/toc.py                                                    |       41 |        1 |       22 |        1 |     96.83% |        52 |
| core/utils.py                                                  |        6 |        0 |        2 |        0 |    100.00% |           |
| core/views/\_\_init\_\_.py                                     |        0 |        0 |        0 |        0 |    100.00% |           |
| core/views/account\_delete.py                                  |       47 |        1 |        6 |        1 |     96.23% |        39 |
| core/views/address\_search.py                                  |       40 |        3 |        8 |        3 |     87.50% |13, 36, 63 |
| core/views/association\_import.py                              |       75 |        5 |       12 |        2 |     91.95% |62, 113-115, 130 |
| core/views/audit.py                                            |       19 |        0 |        2 |        0 |    100.00% |           |
| core/views/auth\_mixins.py                                     |       76 |        1 |       18 |        1 |     97.87% |        87 |
| core/views/content\_transfer.py                                |       89 |        5 |        8 |        3 |     91.75% |54, 89, 138, 141-142 |
| core/views/data\_export.py                                     |       28 |        0 |        2 |        0 |    100.00% |           |
| core/views/docs.py                                             |       33 |       20 |       10 |        0 |     30.23% |16-17, 20-23, 26-46 |
| core/views/email\_verify.py                                    |       44 |        0 |       10 |        0 |    100.00% |           |
| core/views/health.py                                           |        8 |        0 |        0 |        0 |    100.00% |           |
| core/views/login.py                                            |       39 |        0 |       12 |        0 |    100.00% |           |
| core/views/logout.py                                           |        8 |        0 |        0 |        0 |    100.00% |           |
| core/views/me.py                                               |       16 |        0 |        0 |        0 |    100.00% |           |
| core/views/membership.py                                       |      116 |        8 |       28 |        5 |     90.97% |95, 99-100, 102, 109, 133, 155-156 |
| core/views/notifications.py                                    |       32 |        1 |        6 |        1 |     94.74% |        35 |
| core/views/page\_templates.py                                  |       39 |        1 |        6 |        1 |     95.56% |        61 |
| core/views/password\_reset.py                                  |       81 |        4 |       12 |        3 |     92.47% |77, 90, 113-114, 119-\>127 |
| core/views/profile\_edit.py                                    |      145 |        6 |       32 |        6 |     93.22% |122, 132, 136, 165, 175, 182 |
| core/views/register.py                                         |      108 |        7 |       26 |        7 |     89.55% |105, 118, 124, 131, 133, 135, 212 |
| core/views/tasks.py                                            |       50 |        0 |        6 |        0 |    100.00% |           |
| core/wagtail\_forms.py                                         |       52 |        2 |       12 |        4 |     90.62% |31-\>exit, 39, 59, 71-\>76 |
| core/wagtail\_hooks.py                                         |      158 |        1 |       18 |        4 |     97.16% |35-\>37, 46-\>50, 291, 295-\>exit |
| core/wagtail\_viewsets.py                                      |       19 |        3 |        0 |        0 |     84.21% |     22-24 |
| core/widgets.py                                                |       81 |       18 |       16 |        2 |     69.07% |21, 33-40, 54, 73-76, 86-93 |
| home/\_\_init\_\_.py                                           |        0 |        0 |        0 |        0 |    100.00% |           |
| home/apps.py                                                   |        4 |        0 |        0 |        0 |    100.00% |           |
| home/blocks.py                                                 |      224 |        7 |       20 |        4 |     95.49% |119, 131, 133, 285, 405-407 |
| home/management/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100.00% |           |
| home/management/commands/\_\_init\_\_.py                       |        0 |        0 |        0 |        0 |    100.00% |           |
| home/management/commands/mock\_home\_page\_content.py          |       15 |       15 |        2 |        0 |      0.00% |      1-56 |
| home/models.py                                                 |       19 |        1 |        0 |        0 |     94.74% |        35 |
| home/page\_templates.py                                        |       17 |        0 |        0 |        0 |    100.00% |           |
| legal/\_\_init\_\_.py                                          |        0 |        0 |        0 |        0 |    100.00% |           |
| legal/apps.py                                                  |        4 |        0 |        0 |        0 |    100.00% |           |
| legal/forms.py                                                 |        4 |        0 |        0 |        0 |    100.00% |           |
| legal/management/\_\_init\_\_.py                               |        0 |        0 |        0 |        0 |    100.00% |           |
| legal/management/commands/\_\_init\_\_.py                      |        0 |        0 |        0 |        0 |    100.00% |           |
| legal/management/commands/populate\_legal\_pages.py            |       57 |       57 |       12 |        0 |      0.00% |     1-119 |
| legal/models/\_\_init\_\_.py                                   |        6 |        0 |        0 |        0 |    100.00% |           |
| legal/models/code\_of\_conduct.py                              |       16 |        0 |        0 |        0 |    100.00% |           |
| legal/models/code\_of\_conduct\_consent.py                     |       18 |        0 |        0 |        0 |    100.00% |           |
| legal/models/cookies\_policy.py                                |       16 |        0 |        0 |        0 |    100.00% |           |
| legal/models/legal\_index.py                                   |       14 |        0 |        0 |        0 |    100.00% |           |
| legal/models/privacy\_policy.py                                |       16 |        0 |        0 |        0 |    100.00% |           |
| legal/models/terms\_of\_service.py                             |       16 |        0 |        0 |        0 |    100.00% |           |
| legal/permissions.py                                           |       11 |        0 |        2 |        0 |    100.00% |           |
| legal/utils.py                                                 |       25 |        2 |        8 |        2 |     87.88% |    36, 40 |
| legal/views.py                                                 |       38 |        0 |        6 |        0 |    100.00% |           |
| pedagogy/\_\_init\_\_.py                                       |        0 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/apps.py                                               |        4 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/blocks.py                                             |       12 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/management/\_\_init\_\_.py                            |        0 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/management/commands/\_\_init\_\_.py                   |        0 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/management/commands/create\_mock\_pedagogy\_cards.py  |       37 |       37 |       12 |        0 |      0.00% |      1-61 |
| pedagogy/models/\_\_init\_\_.py                                |        3 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/models/pedagogy\_card.py                              |       35 |        2 |        4 |        0 |     94.87% |    26, 70 |
| pedagogy/models/pedagogy\_index.py                             |       50 |        5 |        2 |        1 |     88.46% |70, 79, 99-105 |
| pedagogy/models/pedagogy\_resource.py                          |       18 |        0 |        4 |        0 |    100.00% |           |
| pedagogy/page\_templates.py                                    |       13 |        0 |        0 |        0 |    100.00% |           |
| publications/\_\_init\_\_.py                                   |        0 |        0 |        0 |        0 |    100.00% |           |
| publications/apps.py                                           |        6 |        0 |        0 |        0 |    100.00% |           |
| publications/blocks.py                                         |       12 |        0 |        0 |        0 |    100.00% |           |
| publications/event\_reminders.py                               |       21 |        0 |        2 |        0 |    100.00% |           |
| publications/geo.py                                            |       60 |        0 |       22 |        0 |    100.00% |           |
| publications/ical.py                                           |       47 |        1 |       14 |        3 |     93.44% |55, 64-\>66, 71-\>73 |
| publications/management/\_\_init\_\_.py                        |        0 |        0 |        0 |        0 |    100.00% |           |
| publications/management/commands/\_\_init\_\_.py               |        0 |        0 |        0 |        0 |    100.00% |           |
| publications/management/commands/build\_map\_tiles.py          |       26 |       10 |        4 |        1 |     63.33% |     43-55 |
| publications/management/commands/create\_mock\_publications.py |       66 |       66 |       22 |        0 |      0.00% |     1-119 |
| publications/management/commands/create\_mock\_votes.py        |       91 |       91 |       30 |        0 |      0.00% |     1-323 |
| publications/management/commands/runserver.py                  |       50 |       12 |       14 |        0 |     68.75% |50-57, 71-74 |
| publications/map\_tiles.py                                     |      114 |       26 |       26 |        3 |     76.43% |63, 69-75, 80-93, 101-117, 137, 187-188, 196-\>200 |
| publications/models/\_\_init\_\_.py                            |       11 |        0 |        0 |        0 |    100.00% |           |
| publications/models/event.py                                   |       55 |        0 |        4 |        1 |     98.31% | 117-\>120 |
| publications/models/event\_interest.py                         |       13 |        1 |        0 |        0 |     92.31% |        35 |
| publications/models/external\_link.py                          |       17 |        0 |        0 |        0 |    100.00% |           |
| publications/models/form.py                                    |       27 |        1 |        0 |        0 |     96.30% |        73 |
| publications/models/idea.py                                    |       17 |        1 |        0 |        0 |     94.12% |        54 |
| publications/models/map\_settings.py                           |       28 |        0 |        0 |        0 |    100.00% |           |
| publications/models/poll\_closure.py                           |       16 |        1 |        0 |        0 |     93.75% |        40 |
| publications/models/project.py                                 |       92 |        0 |       12 |        0 |    100.00% |           |
| publications/models/project\_update.py                         |       18 |        1 |        0 |        0 |     94.44% |        47 |
| publications/models/publication.py                             |       20 |        0 |        0 |        0 |    100.00% |           |
| publications/models/publication\_index.py                      |       58 |        1 |        0 |        0 |     98.28% |        51 |
| publications/page\_templates.py                                |       22 |        0 |        0 |        0 |    100.00% |           |
| publications/polls.py                                          |       34 |        0 |        6 |        0 |    100.00% |           |
| publications/project\_updates.py                               |       28 |        1 |        6 |        1 |     94.12% |        38 |
| publications/services.py                                       |       75 |        0 |       14 |        0 |    100.00% |           |
| publications/signals.py                                        |        7 |        0 |        0 |        0 |    100.00% |           |
| publications/tasks.py                                          |       25 |        4 |        0 |        0 |     84.00% |8-10, 32-34 |
| publications/views/\_\_init\_\_.py                             |        0 |        0 |        0 |        0 |    100.00% |           |
| publications/views/event\_interest.py                          |       35 |        2 |        8 |        2 |     90.70% |    41, 56 |
| publications/views/feeds.py                                    |       49 |        0 |        2 |        0 |    100.00% |           |
| publications/views/idea.py                                     |       56 |        6 |       20 |        5 |     85.53% |27-28, 73, 76, 88, 109, 120-\>131 |
| publications/views/idea\_stats.py                              |       42 |        0 |        2 |        0 |    100.00% |           |
| publications/views/map\_tiles.py                               |       16 |        0 |        4 |        0 |    100.00% |           |
| publications/views/mixins.py                                   |       47 |        0 |       18 |        0 |    100.00% |           |
| publications/views/poll\_close.py                              |       26 |        2 |        4 |        2 |     86.67% |    24, 41 |
| publications/views/vote.py                                     |       66 |        7 |       26 |        6 |     85.87% |34-35, 87, 90, 96, 108, 130, 138-\>153 |
| publications/views/vote\_stats.py                              |       61 |        0 |        8 |        0 |    100.00% |           |
| publications/wagtail\_hooks.py                                 |       52 |        6 |        4 |        0 |     85.71% |78-80, 86, 94, 103 |
| publications/widgets.py                                        |       32 |        0 |        2 |        0 |    100.00% |           |
| **TOTAL**                                                      | **6975** |  **664** | **1198** |  **158** | **88.25%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/neikow/urban-platform/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/neikow/urban-platform/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/neikow/urban-platform/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/neikow/urban-platform/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fneikow%2Furban-platform%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/neikow/urban-platform/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.