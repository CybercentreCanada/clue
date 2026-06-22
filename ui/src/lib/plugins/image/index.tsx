import type { RenderActionResultProps, RenderFetcherResultProps } from '../ClueUIPlugin';
import ClueUIPlugin from '../ClueUIPlugin';

class ImagePlugin extends ClueUIPlugin {
  name = 'ImagePlugin';
  format = 'image';
  version = '1.0.0';
  author = 'Canadian Centre for Cyber Security <some.email@cyber.gc.ca>';
  description = 'Renders images.';

  actionResult(props: RenderActionResultProps) {
    const { result, ...additionalProps } = props;
    return <img src={result.output.image} alt={result.output.alt} {...additionalProps} />;
  }

  fetcherResult(props: RenderFetcherResultProps) {
    const { result, ...additionalProps } = props;
    return <img src={result.data.image} alt={result.data.alt} {...additionalProps} />;
  }
}
export default ImagePlugin;
