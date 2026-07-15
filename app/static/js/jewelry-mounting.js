/* 飾品戒台費用 helpers — shared with diamond-calculator jewelry_mounting.py
   (ring mounting table + ring-size surcharge). Used by configurator.js. */
(function (global) {
  'use strict';

  var RING_MOUNTING_REFERENCE_SIZE = 9;
  var RING_SIZE_SURCHARGE_PRE_TAX_PER_HALF = 500;

  function ringSizeSurchargePreTax(ringSize) {
    var size = parseFloat(ringSize);
    if (isNaN(size) || size <= RING_MOUNTING_REFERENCE_SIZE) return 0;
    var halfSteps = (size - RING_MOUNTING_REFERENCE_SIZE) * 2;
    return Math.round(halfSteps * RING_SIZE_SURCHARGE_PRE_TAX_PER_HALF);
  }

  function mountingFeePreTax(pricing, jewelryType, metal, ringSize) {
    var table = (pricing && pricing.mounting && pricing.mounting[jewelryType]) || {};
    var base = table[metal] != null ? table[metal] : 0;
    if (jewelryType === 'ring') {
      return base + ringSizeSurchargePreTax(ringSize);
    }
    return base;
  }

  global.ImprintJewelryMounting = {
    ringMountingReferenceSize: RING_MOUNTING_REFERENCE_SIZE,
    ringSizeSurchargePreTax: ringSizeSurchargePreTax,
    mountingFeePreTax: mountingFeePreTax,
  };
}(typeof window !== 'undefined' ? window : this));
