export const fcoseLayout = {
  name: 'fcose',
  animate: true,
  animationDuration: 500,
  fit: true,
  padding: 50,
  nodeDimensionsIncludeLabels: true,
  uniformNodeDimensions: false,
  packComponents: true,
  nodeRepulsion: 4500,
  idealEdgeLength: 100,
  edgeElasticity: 0.45,
  nestingFactor: 0.1,
  gravity: 0.25,
  gravityRange: 3.8,
  numIter: 2500,
  tile: true,
  tilingPaddingVertical: 10,
  tilingPaddingHorizontal: 10,
};

export const circleLayout = {
  name: 'circle',
  animate: true,
  animationDuration: 500,
  fit: true,
  padding: 50,
  avoidOverlap: true,
};

export const gridLayout = {
  name: 'grid',
  animate: true,
  animationDuration: 500,
  fit: true,
  padding: 50,
  avoidOverlap: true,
  condense: true,
};

export const breadthfirstLayout = {
  name: 'breadthfirst',
  animate: true,
  animationDuration: 500,
  fit: true,
  padding: 50,
  directed: true,
  spacingFactor: 1.5,
};

export const layouts: Record<string, object> = {
  fcose: fcoseLayout,
  circle: circleLayout,
  grid: gridLayout,
  breadthfirst: breadthfirstLayout,
};
