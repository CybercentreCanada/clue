import type { RenderActionResultProps, RenderFetcherResultProps } from '../ClueUIPlugin';
import ClueUIPlugin from '../ClueUIPlugin';

class ImagePlugin extends ClueUIPlugin {
  name = 'ImagePlugin';
  format = 'image';
  version = '1.0.0';
  author = 'Canadian Centre for Cyber Security Matthew.Rafuse@cyber.gc.ca';
  description = 'Renders images.';

  actionResult(props: RenderActionResultProps) {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { result, fetcherId: _fetcherId, ...additionalProps } = props;
    return <img src={result.output.image} alt={result.output.alt} {...additionalProps} />;
  }

  fetcherResult(props: RenderFetcherResultProps) {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { result, fetcherId: _fetcherId, ...additionalProps } = props;
    return <img src={result.data.image} alt={result.data.alt} {...additionalProps} />;
  }
}
export default ImagePlugin;
