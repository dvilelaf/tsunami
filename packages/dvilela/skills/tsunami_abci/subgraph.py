"""Subgraph queries"""

from string import Template


OMEN_XDAI_FPMMS_QUERY = Template(
    """
    {
      fixedProductMarketMakers(
        where: {
          creator: "0x89c5cc945dd550bcffb72fe42bff002429f46fec",
          creationTimestamp_gt: "${creationTimestamp_gt}"
        }
        orderBy: creationTimestamp
        orderDirection: asc
        first: 100
      ) {
        question {
          title
        }
        id
        creationTimestamp
      }
    }
    """
)

OMEN_XDAI_TRADES_QUERY = Template(
    """
    {
        fpmmTrades(
            where: {
                type: Buy,
                fpmm_: {
                    creator: "0x89c5cc945dd550bcffb72fe42bff002429f46fec",
                },
                creationTimestamp_gt: "${creationTimestamp_gt}"
            }
            first: 1000
            orderBy: creationTimestamp
            orderDirection: asc
        ) {
            id
            title
            creator {
                id
            }
            collateralAmountUSD
        }
    }
    """
)


PACKAGE_QUERY = """
query getPackages($package_type: String!) {
    units(where: {packageType: $package_type}) {
        id,
        packageType,
        publicId,
        packageHash,
        tokenId,
        metadataHash,
        description,
        owner,
        image
    }
}
"""
