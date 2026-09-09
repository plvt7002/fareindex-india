/**
 * FareIndex India — Route Coverage Configuration
 *
 * Distinguishes verified tracked routes from planned coverage routes.
 * IMPORTANT: Planned routes NEVER enter statistical calculations, index generation,
 * or API fetching. They are UI-presentation only.
 */

export const ROUTE_CATALOG = {
  'HYD-DEL': {
    code: 'HYD-DEL',
    originCode: 'HYD',
    destCode: 'DEL',
    originName: 'Hyderabad',
    destName: 'Delhi',
    status: 'TRACKED',
    badge: 'Verified Baseline',
    badgeType: 'verified',
    description: 'Trunk business & leisure corridor with verified historical baseline.',
  },
  'HYD-GOI': {
    code: 'HYD-GOI',
    originCode: 'HYD',
    destCode: 'GOI',
    originName: 'Hyderabad',
    destName: 'Goa',
    status: 'TRACKED',
    badge: 'Building Baseline',
    badgeType: 'building',
    description: 'High-season leisure corridor with ongoing observation history.',
  },
  'HYD-BOM': {
    code: 'HYD-BOM',
    originCode: 'HYD',
    destCode: 'BOM',
    originName: 'Hyderabad',
    destName: 'Mumbai',
    status: 'COMING_SOON',
    badge: 'Coming Soon',
    badgeType: 'planned',
    description: 'High-frequency metro corridor scheduled for automated daily observation.',
  },
  'DEL-BOM': {
    code: 'DEL-BOM',
    originCode: 'DEL',
    destCode: 'BOM',
    originName: 'Delhi',
    destName: 'Mumbai',
    status: 'COMING_SOON',
    badge: 'Coming Soon',
    badgeType: 'planned',
    description: 'Busiest domestic air corridor planned for upcoming index expansion.',
  },
};

export const TRACKED_ROUTES = [
  ROUTE_CATALOG['HYD-DEL'],
  ROUTE_CATALOG['HYD-GOI'],
];

export const COMING_SOON_ROUTES = [
  ROUTE_CATALOG['HYD-BOM'],
  ROUTE_CATALOG['DEL-BOM'],
];
